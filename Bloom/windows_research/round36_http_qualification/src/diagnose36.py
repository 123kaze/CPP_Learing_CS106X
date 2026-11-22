"""Fixed, development-only model/repetition diagnostics. No filter outcome selection."""
import os
for _v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_v] = '1'
from pathlib import Path
import time
from statistics import median
import numpy as np
import lightgbm as lgb
from scipy.stats import rankdata

SEEDS = (3601, 3602, 3603)


def splitmix64(x):
    with np.errstate(over='ignore'):
        z = x.astype(np.uint64) + np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return z ^ (z >> np.uint64(31))


def split(ids, y, first, boundary, seed):
    u = (splitmix64(ids ^ np.uint64(seed)) >> np.uint64(11)).astype(float)/2**53
    early = first < boundary
    result = dict(member_train=y & (u<.5), neg_train=(~y)&early&(u<.1),
                  neg_val=(~y)&early&(u>=.1)&(u<.2))
    result['neg_test'] = (~y)&~(result['neg_train']|result['neg_val'])
    assert not np.any(result['neg_test'] & (result['neg_train']|result['neg_val']))
    return result


def auc(y, score):
    n = int(y.sum()); m = len(y)-n
    return float((rankdata(score)[y].sum()-n*(n+1)/2)/(n*m)) if n*m else None


def diagnose(path, seed):
    start = time.perf_counter()
    with np.load(path, allow_pickle=False) as f:
        ids, y, X, first, trace, order, boundary = [f[k] for k in ('ids','y','X','first','trace','order','boundary')]
    sp = split(ids, y, first, int(boundary), seed)
    position = np.full(len(ids), -1, np.int64); position[sp['neg_test']] = np.arange(sp['neg_test'].sum())
    q = position[trace]
    learn = q[(q>=0)&(order<int(boundary))]; tail = q[(q>=0)&(order>=int(boundary))]
    counts = np.bincount(learn, minlength=int(sp['neg_test'].sum()))
    features = X.view(np.dtype((np.void, X.dtype.itemsize*X.shape[1]))).ravel()
    overlapping = int(np.isin(features[sp['neg_test']], features[y]).sum())
    pool = int(sp['neg_test'].sum())
    new_keys = first[sp['neg_test']] >= int(boundary)
    out = dict(seed=seed, status='complete', train_members=int(sp['member_train'].sum()),
               train_negatives=int(sp['neg_train'].sum()), validation_negatives=int(sp['neg_val'].sum()),
               negative_pool=pool, learning_requests=len(learn), tail_requests=len(tail),
               learning_distinct=int((counts>0).sum()), learning_repeat_fraction=1-float((counts>0).sum())/len(learn) if len(learn) else 0.,
               tail_distinct=len(np.unique(tail)), tail_new_key_request_fraction=float(new_keys[tail].mean()) if len(tail) else None,
               negative_keys_sharing_features_with_members=overlapping, feature_overlap_fraction=overlapping/pool if pool else 0.,
               development_auc=None, regions=[], supported_regions=0, region_repeat_gap=0.,
               requested_trees=16, actual_trees=0, training_s=0., scoring_s=0., native_threads=1)
    if min(out['train_members'], out['train_negatives'], out['validation_negatives']) < 20 or not np.any(y & ~sp['member_train']):
        out.update(status='insufficient_development_support', wall_s=time.perf_counter()-start)
        return out
    training = sp['member_train']|sp['neg_train']
    t = time.perf_counter()
    model = lgb.train(dict(objective='binary', num_leaves=31, learning_rate=.1, num_threads=1,
                           seed=seed, deterministic=True, force_col_wise=True, verbose=-1),
                      lgb.Dataset(X[training], label=y[training]), num_boost_round=16)
    out['training_s'] = time.perf_counter()-t; out['actual_trees'] = model.num_trees()
    t = time.perf_counter(); score = model.predict(X, raw_score=True, num_threads=1)
    out['scoring_s'] = time.perf_counter()-t
    held = (y & ~sp['member_train'])|sp['neg_val']
    out['development_auc'] = auc(y[held], score[held])
    cuts = np.unique(np.quantile(score[sp['neg_val']], [.2,.4,.6,.8], method='linear'))
    reg = np.searchsorted(cuts, score[sp['neg_test']], side='left')
    mr = np.searchsorted(cuts, score[y], side='left')
    for r in range(len(cuts)+1):
        c = counts[reg==r]; n = int(c.sum()); distinct = int((c>0).sum())
        out['regions'].append(dict(region=r, members=int((mr==r).sum()), pool_keys=len(c),
                                   learning_requests=n, learning_distinct=distinct, learning_singleton_keys=int((c==1).sum()),
                                   repeat_fraction=1-distinct/n if n else None))
    supported = [r['repeat_fraction'] for r in out['regions'] if r['learning_distinct']>=50]
    out['supported_regions'] = len(supported)
    out['region_repeat_gap'] = max(supported)-min(supported) if len(supported)>=2 else 0.
    out['region_raw_score_cuts'] = cuts.tolist()
    out['diagnostic_s_excluding_training_and_scoring'] = time.perf_counter()-start-out['training_s']-out['scoring_s']
    out['wall_s'] = time.perf_counter()-start
    return out


def qualify(meta, diagnostics):
    assert len(diagnostics)==3 and {r['seed'] for r in diagnostics}==set(SEEDS)
    def mid(field): return median(r[field] for r in diagnostics)
    auc_values = [r['development_auc'] for r in diagnostics]
    checks = dict(
        members_ge_10000=meta['members']>=10000,
        negative_keys_ge_1000=meta['negative_keys']>=1000,
        retained_404_requests_ge_10000=meta['retained_404_requests']>=10000,
        retained_404_fraction_ge_090=meta['retained_404_fraction']>=.90,
        median_learning_requests_ge_1000=mid('learning_requests')>=1000,
        median_tail_requests_ge_1000=mid('tail_requests')>=1000,
        all_seed_training_and_validation_support_ge_20=all(min(r['train_negatives'],r['validation_negatives'])>=20 for r in diagnostics),
        median_feature_overlap_ge_001=mid('feature_overlap_fraction')>=.01,
        median_development_auc_ge_070=all(a is not None for a in auc_values) and median(auc_values)>=.70,
        median_learning_repeat_fraction_ge_010=mid('learning_repeat_fraction')>=.10,
        median_supported_regions_ge_2=mid('supported_regions')>=2,
        median_region_repeat_gap_ge_010=mid('region_repeat_gap')>=.10,
    )
    return dict(eligible_for_full_comparison=all(checks.values()), checks=checks,
                failed_checks=[k for k,v in checks.items() if not v], larger_catalog_ge_50000=meta['members']>=50000,
                modern_workload=False, median_development_auc=median(auc_values) if all(a is not None for a in auc_values) else None,
                median_learning_repeat_fraction=mid('learning_repeat_fraction'), median_region_repeat_gap=mid('region_repeat_gap'),
                median_feature_overlap_fraction=mid('feature_overlap_fraction'))

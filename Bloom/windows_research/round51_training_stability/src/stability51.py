import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent
sys.path.insert(0,str(WR/'round50_sis_fullfile_diagnostics/src'))
import prepare50 as P
from prepare50 import W,E5,np,sha,save
import json,time,resource
RECIPES=('original','balanced','clip_only','balanced_clip')


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in f[group].items():assert sha(BLOOM/p)==h,p


def weights(labels):
    n=len(labels);positive=int(labels.sum());negative=n-positive
    if min(positive,negative)<=0:raise ValueError('Bothclasses required')
    return np.where(labels,n/(2*positive),n/(2*negative)).astype(np.float64)


def params(seed,recipe):
    assert recipe in RECIPES
    p=dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1)
    if recipe in ('clip_only','balanced_clip'):p['max_delta_step']=1.
    return p


def run(seed):
    check();start=time.perf_counter();path=ROOT/f'results/seed{seed}.json';assert not path.exists()
    ids,y,X,split,learn,tail,_=P.load(seed);train=split['member_train']|split['neg_train'];held=(y&~split['member_train'])|split['neg_val'];assert not np.any(train&held)
    old=json.loads((WR/f'round50_sis_fullfile_diagnostics/results/seed{seed}.json').read_text())
    assert W.ah(learn)==old['learning_sha256'] and W.ah(tail)==old['tail_sha256']
    out=dict(status='running',seed=seed,train_members=int(split['member_train'].sum()),train_negatives=int(split['neg_train'].sum()),validation_negatives=int(split['neg_val'].sum()),learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),rows=[])
    for recipe in RECIPES:
        t=time.perf_counter();w=weights(y[train]) if recipe in ('balanced','balanced_clip') else None;weight_s=time.perf_counter()-t
        pos=float(w[y[train]].sum()) if w is not None else float(y[train].sum());neg=float(w[~y[train]].sum()) if w is not None else float((~y[train]).sum());init_logit=float(np.log(pos/neg))
        t=time.perf_counter();model=W.lgb.train(params(seed,recipe),W.lgb.Dataset(X[train],label=y[train],weight=w),num_boost_round=16);train_s=time.perf_counter()-t
        t=time.perf_counter();score=model.predict(X,raw_score=True,num_threads=1);score_s=time.perf_counter()-t
        assert np.isfinite(score).all()
        if recipe in ('clip_only','balanced_clip'):assert np.max(np.abs(score-init_logit))<=16*.1+1e-5,'Leafstep clipping bound violated'
        t=time.perf_counter();auc=W.auc(y[held],score[held]);auc_s=time.perf_counter()-t
        if recipe=='original':assert np.isclose(auc,old['development_auc16'],rtol=0,atol=1e-12)
        with np.errstate(over='ignore'):sigmoid=1/(1+np.exp(-score))
        seg=E5.D.segment_of(sigmoid)
        row=dict(recipe=recipe,development_auc=auc,actual_trees=model.num_trees(),positive_weight_mass=pos,negative_weight_mass=neg,initial_logit=init_logit,raw_score_min=float(score.min()),raw_score_max=float(score.max()),finite_scores=True,member_occupied_bins=len(np.unique(seg[y])),validation_negative_occupied_bins=len(np.unique(seg[split['neg_val']])),member_fraction_bin999=float((seg[y]==999).mean()),validation_negative_fraction_bin999=float((seg[split['neg_val']]==999).mean()),weight_build_s=weight_s,weight_array_bytes=sys.getsizeof(w) if w is not None else 0,training_s=train_s,score_s=score_s,auc_s=auc_s,score_direction_flipped=False,method_FP_evaluated=False)
        out['rows'].append(row);save(path,out);print('RECIPE',seed,recipe,'AUC',auc,'bins',row['member_occupied_bins'],row['validation_negative_occupied_bins'],flush=True)
    out.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);assert out['peak_rss_bytes']<=4*1024**3;check();save(path,out)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('seed',type=int,choices=P.SEEDS);a=p.parse_args()
    try:run(a.seed)
    except Exception as e:save(ROOT/f'results/seed{a.seed}.failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300]));raise

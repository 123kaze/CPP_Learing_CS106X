"""Isolated Windows runtime. All mutable paths live inside windows_research."""
from pathlib import Path
import sys
import json
import time
import sys as _sys
import numpy as np
import lightgbm as lgb
from numba import njit

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / 'vendor' / 'original_src'
sys.path.insert(0, str(ORIGINAL))
import common as C
C.PROJECT = ROOT
C.CACHE = ROOT / 'cache'
C.RESULTS = ROOT / 'results'
C.FIGURES = ROOT / 'figures'
C.HTTYF_DATA = ROOT / 'data'
for _ds in ('caida', 'caida_flow'):
    C.DATASETS[_ds]['raw'] = ROOT / 'data' / 'caida.csv'
C.DATASETS['cod']['raw'] = ROOT.parent / 'LBF-Gama' / 'dataset' / 'raw' / 'cod'
for _ds in ('mawi2020_flow', 'mawi2021_flow'):
    C.DATASETS[_ds]['raw'] = ROOT / 'data' / (_ds.removesuffix('_flow') + '.csv')
from exp11_original_baselines import GAMA_TREES, gama_setup
from exp2_repetition_cache import make_stream, workloads
_MODEL_ARRAYS = {}
_GSETUPS = {}

def prepare(ds, threads=8):
    out = C.CACHE / ds
    out.mkdir(parents=True, exist_ok=True)
    ids, y, X, features = C.load_dataset(ds)
    sp = C.make_split(ids, y, ds)
    train = sp['member_train'] | sp['neg_train']
    model_path = out / 'model200.txt'
    t0 = time.perf_counter()
    if model_path.exists():
        model = lgb.Booster(model_file=str(model_path))
    else:
        model = lgb.train(dict(objective='binary', num_leaves=31, learning_rate=.1,
                             num_threads=threads, verbose=-1, seed=1,
                             deterministic=True, force_col_wise=True),
                          lgb.Dataset(X[train], label=y[train], feature_name=features), num_boost_round=200)
        model.save_model(str(model_path))
    score_path = out / 'gama_scores.npz'
    if not score_path.exists():
        scores = {}
        for t in GAMA_TREES:
            scores['t'+str(t)] = model.predict(X, raw_score=True, num_iteration=t, num_threads=threads)
            print(f'{ds}: scored {t} trees', flush=True)
        np.savez(score_path, **scores)
        np.savez(out / 'scores.npz', score=scores['t48'])
        model.save_model(str(out / 'model48.txt'), num_iteration=48)
    meta = dict(dataset=ds, rows=len(ids), members=int(y.sum()), features=features,
                split={k:int(v.sum()) for k,v in sp.items()},
                preparation_seconds=time.perf_counter()-t0,
                lightgbm_version=lgb.__version__, raw=str(C.DATASETS[ds]['raw']))
    (out/'preparation.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps(meta), flush=True)
    return meta

def load_setup(ds):
    s = C.Setup(ds)
    s.member_hashes = np.sort(s.h1m)
    return s

def scores_for(setup, ds=None):
    with np.load(C.CACHE / (ds or setup.name) / 'gama_scores.npz') as a:
        return {int(k[1:]): a[k] for k in a.files}

@njit(cache=True)
def packed_build(hashes, regions, off, sizes, ks, bits):
    for i in range(len(hashes)):
        g = regions[i]
        if sizes[g] <= 0:
            continue
        for j in range(ks[g]):
            p = off[g] + C.bf_pos(hashes[i], j, sizes[g])
            bits[p >> 3] |= np.uint8(1 << (p & 7))

@njit(cache=True)
def packed_query(hashes, regions, kinds, off, sizes, ks, bits):
    out = np.zeros(len(hashes), np.bool_)
    for i in range(len(hashes)):
        g = regions[i]
        if kinds[g] == C.PASS:
            out[i] = True
        elif kinds[g] == C.BF:
            ok = True
            for j in range(ks[g]):
                p = off[g] + C.bf_pos(hashes[i], j, sizes[g])
                if (bits[p >> 3] >> (p & 7)) & 1 == 0:
                    ok = False
                    break
            out[i] = ok
    return out

def structure(setup, scores, t, budget_bytes, cache_bytes, sketch_bytes=5128):
    """Packed BF + actual packed tree and navigation array byte accounting."""
    from types import SimpleNamespace
    from end_to_end import model_arrays
    key = (setup.name, t)
    if key not in _MODEL_ARRAYS:
        booster = lgb.Booster(model_file=str(C.CACHE/setup.name/'model200.txt'))
        _MODEL_ARRAYS[key] = model_arrays(booster, t)
    arrays = _MODEL_ARRAYS[key]
    model_bytes = sum(a.nbytes for a in arrays.values())
    if (id(setup),t) not in _GSETUPS:
        _GSETUPS[id(setup),t] = gama_setup(setup, scores[t])
    gs = _GSETUPS[id(setup),t]
    cuts = gs.cuts.astype(np.float64)
    nr = len(cuts)+1
    # These arrays are the deployed navigation representation, also consumed by end_to_end.
    metadata_bytes = cuts.nbytes + nr*(1+8+8) + (nr+1)*8
    # Owning ndarray headers: six model, five navigation, one BF, six sketch.
    # A dict holding the model arrays is also charged. Inputs/training state and
    # interpreter/JIT code are reported as host infrastructure, outside the AMQ.
    ah = _sys.getsizeof(np.empty(0,np.uint8))
    array_overhead_bytes = (12 + (6 if sketch_bytes else 0))*ah + _sys.getsizeof(arrays)
    fixed = model_bytes + metadata_bytes + array_overhead_bytes + sketch_bytes + cache_bytes
    if fixed >= budget_bytes:
        return None
    regions = np.searchsorted(cuts, gs.mem_score, side='right').astype(np.int32)
    n = np.bincount(regions, minlength=nr).astype(np.float64)
    cnt = np.bincount(np.searchsorted(cuts, gs.val_score, side='right'), minlength=nr)
    h = (cnt+.5)/(cnt.sum()+.5*nr)
    kind,param,_,est = C.allocate(n,h,(budget_bytes-fixed)*8,'bf')
    kind = kind.astype(np.uint8)
    m = np.where(kind==C.BF, np.maximum(1,np.floor(param*n)),0).astype(np.int64)
    k = np.where(kind==C.BF, np.maximum(1,np.rint(param*np.log(2))),0).astype(np.int64)
    off = np.concatenate([[0],np.cumsum(m)]).astype(np.int64)
    bits = np.zeros((int(off[-1])+7)//8,np.uint8)
    packed_build(setup.h1m,regions,off,m,k,bits)
    accepted_members = packed_query(setup.h1m,regions,kind,off,m,k,bits)
    assert accepted_members.all(), 'Packed Bloom false negative'
    rq = np.searchsorted(cuts, gs.q_score, side='right').astype(np.int32)
    fp = packed_query(setup.h1q,rq,kind,off,m,k,bits)
    used = fixed + bits.nbytes
    assert used <= budget_bytes
    return SimpleNamespace(name=f't{t}', trees=t, cuts=cuts, kind=kind, m=m, k=k,
                           bf_off=off, bits=bits, fp_static=fp, est_fpr=est,
                           in_pass_q=kind[rq]==C.PASS, model_arrays=arrays,
                           model_bytes=model_bytes, metadata_bytes=metadata_bytes,
                           array_overhead_bytes=array_overhead_bytes,
                           filter_bytes=bits.nbytes, cache_bytes=cache_bytes,
                           sketch_bytes=sketch_bytes, used_bytes=used,
                           budget_bytes=budget_bytes, member_false_negatives=0)

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--prepare', required=True)
    p.add_argument('--threads',type=int,default=8)
    a=p.parse_args()
    prepare(a.prepare,a.threads)

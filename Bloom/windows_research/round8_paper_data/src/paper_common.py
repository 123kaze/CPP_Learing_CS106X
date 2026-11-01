"""Paper-source fixtures with frozen learning and held-out workloads."""
import os
for name in ('OMP_NUM_THREADS', 'NUMBA_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BLOOM = ROOT.parents[1]
sys.path.insert(0, str(ROOT.parent / 'round7_original_e2e' / 'src'))
import shared as S
S.ROOT = ROOT


def data(ds):
    with np.load(ROOT / 'data' / ds / 'data.npz') as a:
        ids, y, X = a['ids'], a['y'], a['X']
        features = [str(x) for x in a['features']]
        sp = {k:a[k] for k in ('member_train', 'neg_train', 'neg_val', 'neg_test')}
    return ids, y, X, features, sp


def prepare(ds):
    dest = ROOT / 'inputs' / ds
    if (dest / 'meta.json').exists():
        return
    ids, y, X, features, sp = data(ds)
    nm, nq = int(y.sum()), int(sp['neg_test'].sum())
    dest.mkdir(parents=True, exist_ok=True)
    np.save(dest / 'member_ids.npy', ids[y])
    np.save(dest / 'query_ids.npy', ids[sp['neg_test']])
    audit = json.loads((ROOT / 'data' / ds / 'audit.json').read_text())
    for name in ('once', 'zipf'):
        if name == 'once':
            stream = np.random.default_rng(2000).permutation(nq).astype(np.int64)
        else:
            # Same frozen workload generator, but on the paper-source negative pool.
            sys.path.insert(0, str(ROOT.parent / 'round6_bucket' / 'src'))
            import e789 as J
            import exp2_repetition_cache as E2
            E2.QUERIES = 10000000
            stream = J.R.make_stream(('zipf', None, 1.0), nq, np.random.default_rng(2000), np.arange(nq))
        n = len(stream) // 4
        np.save(dest / f'{name}_learn.npy', stream[:n])
        np.save(dest / f'{name}_tail.npy', stream[n:])
    S.save(dest / 'meta.json', dict(dataset=ds, members=nm, negative_pool=nq, features=features,
                                   data_sha256=audit['data_sha256'], exact_paper_split=False))
    print(f'FIXTURE {ds}: {nm} members, {nq} held-out negatives', flush=True)


def measure_queries(run, fresh, ds, workload):
    folder = ROOT / 'inputs' / ds
    meta = json.loads((folder / 'meta.json').read_text())
    nm = meta['members']
    tail = np.load(folder / f'{workload}_tail.npy') + nm
    result = S.measure(run, fresh, tail, 1000, len(tail))
    return result


def full_pool(run, fresh, ds):
    folder = ROOT / 'inputs' / ds
    meta = json.loads((folder / 'meta.json').read_text())
    idx = np.arange(meta['negative_pool'], dtype=np.int64) + meta['members']
    return S.measure(run, fresh, idx, 1000, len(idx))

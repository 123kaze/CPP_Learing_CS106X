"""Shared real-query measurement, with no precomputed score/FP shortcut."""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMBA_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
import argparse
import hashlib
import json
import platform
import resource
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BLOOM = ROOT.parents[1]
SETTINGS = {'caida_flow': 24, 'url': 128, 'mawi2020_flow': 24, 'mawi2021_flow': 24,
            'mawi2022_flow': 24, 'caida': 256, 'shalla': 1024, 'cod': 1024}


def arguments():
    p = argparse.ArgumentParser()
    p.add_argument('dataset')
    p.add_argument('budget', type=int)
    p.add_argument('output', type=Path)
    return p.parse_args()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def fixture(ds):
    folder = ROOT / 'inputs' / ds
    meta = json.loads((folder / 'meta.json').read_text())
    return folder, meta


def measure(run, fresh, stream, batch, negative_count):
    state = fresh()
    total = np.zeros(6, np.int64)
    chunks = []
    start = time.perf_counter()
    for lo in range(0, len(stream), batch):
        hi = min(lo + batch, len(stream))
        t = time.perf_counter_ns()
        cnt = run(stream, lo, hi, state)
        chunks.append((time.perf_counter_ns() - t) / (hi - lo))
        total += cnt
    seconds = time.perf_counter() - start
    assert total[2] == 0, ('false negatives during queries', int(total[2]))
    return dict(queries=len(stream), negatives=negative_count, fp=int(total[1]), fn=int(total[2]),
                fpr=int(total[1]) / max(1, negative_count), seconds=seconds,
                ns_per_query=seconds * 1e9 / len(stream), batch=batch,
                chunk_mean_ns_p50=float(np.median(chunks)), chunk_mean_ns_p99=float(np.quantile(chunks, .99)),
                cache_hits=int(total[3]), model_calls=int(total[4]))


def evaluate(run, fresh, ds):
    folder, meta = fixture(ds)
    neg = np.load(folder / 'tail.npy') + meta['members']
    mixed = np.load(folder / 'mixed.npy')
    out = {}
    for name, stream, batch in (('negative_tail', neg, 1000), ('mixed_batch', mixed, 1000),
                                 ('mixed_scalar', mixed[:20000], 1)):
        out[name] = measure(run, fresh, stream, batch, int((stream >= meta['members']).sum()))
        print(f'QUERY {ds} {name}: {out[name]}', flush=True)
    return out


def finish(out, path):
    out.update(python=platform.python_version(), numpy=np.__version__,
               peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               threads=1, platform=platform.platform())
    save(path, out)
    print(f'COMPLETE {out["method"]} {out["dataset"]} {out["budget_kib"]}: {out["status"]}', flush=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

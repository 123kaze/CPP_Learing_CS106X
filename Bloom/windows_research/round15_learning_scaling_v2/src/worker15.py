"""Fresh-process selection benchmark. Result hashes and checks are outside timers."""
import os
for v in ('OMP_NUM_THREADS', 'NUMBA_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[v] = '1'
import argparse
import json
import platform
import resource
import sys
import time
import traceback
from pathlib import Path
import numpy as np
from common15 import *
from selection15 import *
from numba import get_num_threads


def main(a):
    out = dict(status='running', method=a.method, L=a.length, rep=a.rep, dataset=DATASET, budget_kib=KIB,
               horizon=3*a.length, pilot=a.pilot, worker_sha256=digest(Path(__file__)))
    try:
        t = time.perf_counter()
        meta = json.loads((ROOT/'inputs/manifest.json').read_text())
        mapping = np.load(ROOT/'inputs/learning.npy', mmap_mode='r')
        learn = np.array(mapping[:a.length], copy=True)  # resident, contiguous, identical input type
        del mapping
        assert array_hash(learn) == meta['prefix_sha256'][str(a.length)]
        out['stream_sha256'] = meta['prefix_sha256'][str(a.length)]
        setup, scores, safe = E5.load(DATASET)
        assert len(setup.h1q) == meta['n_pool'] and array_hash(setup.q_ids) == meta['pool_ids_sha256']
        tds = prepare_shared(setup, scores)
        out['read_and_model_input_prepare_s'] = time.perf_counter()-t
        out['candidate_grid'] = descriptors(setup, scores)
        out['candidate_grid_sha256'] = __import__('hashlib').sha256(json.dumps(out['candidate_grid']).encode()).hexdigest()
        out['pool_keys'] = len(setup.h1q)
        out['learning_trace_bytes'] = learn.nbytes
        # Warm compiled kernels only on a small unrelated learning prefix, never the measured L.
        t = time.perf_counter()
        short = learn[:min(4096, len(learn))]
        warm = (select_ra(setup, scores, tds, short) if a.method == 'ra6'
                else select_replay(setup, scores, tds, safe, short))
        del warm
        out['warmup_s'] = time.perf_counter()-t
        fn = select_ra if a.method == 'ra6' else select_replay
        args = (setup, scores, tds, learn) if a.method == 'ra6' else (setup, scores, tds, safe, learn)
        measured, choice, keys, flags, aux = fn(*args)
        out.update(measured)
        print(f'MEASURED {a.method} L={a.length}: {out["selection_s"]:.3f}s D={out["distinct_keys"]}', flush=True)
        t = time.perf_counter()
        out['choice'] = verify_choice(a.method, setup, scores, safe, learn, choice, keys, flags, aux, a.pilot)
        if a.method == 'replay': assert out['choice']['learning_fp_check'] == out['learning_fp']
        out['verification_s'] = time.perf_counter()-t
        out['thread_environment'] = {v: os.environ[v] for v in ('OMP_NUM_THREADS', 'NUMBA_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')}
        out['numba_threads'] = get_num_threads()
        assert out['numba_threads'] == 1 and set(out['thread_environment'].values()) == {'1'}
        out['status'] = 'ok'
    except Exception:
        out['status'] = 'error';out['error'] = traceback.format_exc();print(out['error'], flush=True)
    out.update(python=platform.python_version(), numpy=np.__version__, platform=platform.platform(),
               peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, threads=1)
    save(a.output, out)
    if out['status'] != 'ok': raise SystemExit(1)
    print(f'COMPLETE {a.method} L={a.length} rep={a.rep}', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--method', choices=('ra6','replay'), required=True)
    p.add_argument('--length', type=int, choices=(PILOT_L,*LENGTHS), required=True)
    p.add_argument('--rep', type=int, choices=range(REPS), required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--pilot', action='store_true')
    a = p.parse_args()
    if a.output.exists():p.error('Output exists; refusing overwrite')
    if a.pilot != (a.length == PILOT_L):p.error('Pilot must use separate pilot length')
    main(a)

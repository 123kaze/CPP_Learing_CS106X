"""One nested 100M-query Zipf stream; bounded generation workspace, no huge tail."""
import os
for v in ('OMP_NUM_THREADS', 'NUMBA_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[v] = '1'
import json
import time
import numpy as np
from common15 import *


def main():
    dest = ROOT / 'inputs'
    file = dest / 'learning.npy'
    meta = dest / 'manifest.json'
    if meta.exists():
        m = json.loads(meta.read_text())
        assert m['status'] == 'complete' and digest(file) == m['file_sha256']
        print('INPUT STREAM ALREADY COMPLETE', flush=True)
        return
    assert not file.exists(), 'Partial stream exists; do not regenerate silently'
    # The negative pool is defined by the actual frozen loader, not a guessed path.
    from selection15 import E5
    setup = E5.R.load_setup(DATASET)
    n_pool = len(setup.h1q)
    pool_ids_hash = array_hash(setup.q_ids)
    del setup
    start = time.perf_counter()
    permutation = np.random.default_rng(PERM_SEED).permutation(n_pool)
    rng = np.random.default_rng(STREAM_SEED)
    cdf = np.cumsum(np.arange(1, n_pool+1, dtype=np.float64)**-1.0)
    cdf /= cdf[-1]
    stream = np.lib.format.open_memmap(file, mode='w+', dtype=np.int64, shape=(max(LENGTHS),))
    for lo in range(0, len(stream), CHUNK):
        hi = min(lo+CHUNK, len(stream))
        ranks = np.minimum(np.searchsorted(cdf, rng.random(hi-lo)), n_pool-1)
        stream[lo:hi] = permutation[ranks]
        if hi in LENGTHS: print(f'GENERATED {hi:,} learning queries', flush=True)
    stream.flush()
    hashes = {str(L): array_hash(stream[:L]) for L in (PILOT_L, *LENGTHS)}
    save(meta, dict(status='complete', dataset=DATASET, n_pool=n_pool, pool_ids_sha256=pool_ids_hash,
                    dtype='int64', queries=len(stream), chunk_rows=CHUNK, permutation_seed=PERM_SEED,
                    stream_seed=STREAM_SEED, zipf_exponent=1.0, prefix_sha256=hashes,
                    file_sha256=digest(file), generation_s=time.perf_counter()-start))
    print('STREAM COMPLETE: nested prefixes, maximum 800 MB payload; no evaluation-tail allocation', flush=True)


if __name__ == '__main__': main()

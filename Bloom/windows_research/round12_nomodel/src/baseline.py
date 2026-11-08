"""A no-model BF with a single owning deployment array; frozen hash/cache code reused."""
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
from numba import njit

HERE = Path(__file__).resolve().parent
WR = HERE.parents[1]
sys.path.insert(0, str(WR / 'round5_dp/src'))
sys.path.insert(0, str(WR / 'round10_fpcache/src'))
import engine5 as E5
import cache_fp

C, R = E5.C, E5.R
HEAD_WORDS = 4
MAGIC = 0x42463132
ARRAY_HEADER = sys.getsizeof(np.empty(0, np.uint64))
CACHES = {'index': E5.K, 'fp64': cache_fp}


def optimal_k(n, m):
    x = m / n * math.log(2)
    choices = {max(1, math.floor(x)), max(1, math.ceil(x))}
    return min(choices, key=lambda k: ((-math.expm1(-k * n / m)) ** k, k))


def allocate(n, budget, cache_bytes):
    words = (budget - cache_bytes - ARRAY_HEADER) // 8
    if n <= 0 or words <= HEAD_WORDS:
        raise ValueError('No space for a nonempty BF')
    data = np.zeros(words, np.uint64)
    m = (words - HEAD_WORDS) * 64
    data[:HEAD_WORDS] = MAGIC, m, optimal_k(n, m), n
    assert data.flags.owndata
    assert sys.getsizeof(data) + cache_bytes <= budget
    return data


@njit(cache=True)
def insert_all(data, hashes):
    m, k = np.int64(data[1]), np.int64(data[2])
    for h in hashes:
        for j in range(k):
            p = C.bf_pos(h, j, m)
            word = HEAD_WORDS + (p >> 6)
            data[word] |= np.uint64(1) << np.uint64(p & 63)


@njit(cache=True)
def query_all(data, hashes):
    m, k = np.int64(data[1]), np.int64(data[2])
    out = np.ones(len(hashes), np.bool_)
    for i in range(len(hashes)):
        for j in range(k):
            p = C.bf_pos(hashes[i], j, m)
            word = HEAD_WORDS + (p >> 6)
            if (data[word] >> np.uint64(p & 63)) & np.uint64(1) == 0:
                out[i] = False
                break
    return out


def build(setup, kib, frac, cache):
    budget = kib * 1024
    spec = cache.layout(int(budget * frac), E5.PREFIX, E5.WAYS)
    cb = spec['allocated_bytes'] if frac > 0 else 0
    data = allocate(len(setup.h1m), budget, cb)
    insert_all(data, setup.h1m)
    assert query_all(data, setup.h1m).all(), 'BF false negative'
    flags = query_all(data, setup.h1q)
    m, k = int(data[1]), int(data[2])
    fpr = (-math.expm1(-k * len(setup.h1m) / m)) ** k
    st = SimpleNamespace(trees=0, data=data, fp_static=flags, est_fpr=fpr,
                         model_bytes=0, metadata_bytes=HEAD_WORDS * 8,
                         array_overhead_bytes=ARRAY_HEADER, filter_bytes=m // 8,
                         used_bytes=sys.getsizeof(data) + cb, budget_bytes=budget)
    return dict(trees=0, frac=float(frac), cache_reserved_bytes=int(budget * frac),
                cache_bytes=cb, slots=spec['slots'] if cb else 0, structure=st)


def load_setup(ds, mode):
    """Read prepared arrays, never train. No model loading or safe-length work for fp64.

    q_score is only a workload-construction input for the frozen fresh/probe streams,
    not a predictor used by the BF. h1m is construction input, not deployed state.
    """
    if ds.endswith('_tcp_flow'):
        sys.path.insert(0, str(WR / 'round11_tcp/src'))
        import tcp11  # registers datasets only; never call prepare
    folder = C.CACHE / ds
    paths = [folder / name for name in ('data.npz', 'scores.npz')]
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError(f'Prepared input required; refusing implicit training: {p}')
    with np.load(paths[0], allow_pickle=False) as data:
        ids, y = data['ids'], data['y']
    split = C.make_split(ids, y, ds)
    with np.load(paths[1], allow_pickle=False) as scores:
        score = scores['score']
    hashes = C.splitmix64(ids ^ np.uint64(C.H1_SALT))
    s = SimpleNamespace(name=ds, ids=ids, split=split, h1m=hashes[y],
                        h1q=hashes[split['neg_test']], q_score=score[split['neg_test']])
    safe = None
    if mode == 'index':
        s.member_hashes = np.sort(s.h1m)
        safe = E5.E.CC.safe_prefix_lengths(s.member_hashes, s.h1q)
    if ds.endswith('_flow'):
        paths.append(folder / 'trace.npy')
    return s, safe, paths

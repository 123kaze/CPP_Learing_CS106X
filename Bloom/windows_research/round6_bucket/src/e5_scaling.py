"""E5 scalability: selection cost of grid replay vs RA6 as one variable grows (single thread).

Base setting: Caida 256KiB (5.8M-key test pool), Zipf s=1.0.  One variable at a time:
  candidates   trees x cache fractions in {6x5, 6x10, 12x20, 12x40}  (pool = all, L = 2.5M)
  learning     L in {1e5, 1e6, 1e7}                                 (14x13 candidates, pool = all)
  keys         Zipf pool in {1e4, 1e5, 1e6, all = 5.8M}              (14x13 candidates, L = 2.5M)
Grid: build every candidate (DP + Bloom insert + query the distinct learning keys) and replay the
learning period in the distinct-key space with early stopping; RA6: RA4 candidate table on the
same candidates, build the 5 best, bucket-load prediction.  Per point: selection seconds (median
of REPS after a warm-up), tracemalloc peak during selection, persistent learning state (grid: the
trace; RA: 16 bytes per distinct key) and the evaluation-segment FP of each method's choice.
usage: e5_scaling.py <candidates|learning|keys>   -> results/e5/<variable>.json
"""
import os
for _v in ('NUMBA_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_v] = '1'
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import tracemalloc  # noqa: E402
from pathlib import Path  # noqa: E402
import numpy as np  # noqa: E402
import ra6  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
E5, RA = ra6.E5, ra6.RA
D, K = E5.D, E5.K
R, C = E5.R, E5.C
DS, KIB, S_ZIPF = 'caida', 256, 1.0
REPS = 3
ALL_TREES = list(E5.TREES)


def frac_grid(n):
    if n == 13:
        return list(E5.FRACS)
    return [0.] + list(np.round(np.geomspace(0.001, 0.6, n - 1), 5))


def tree_grid(n):
    return ALL_TREES if n >= len(ALL_TREES) else [ALL_TREES[i] for i in np.round(np.linspace(0, len(ALL_TREES) - 1, n)).astype(int)]


def dp_bf(setup, td, kib, cache_bytes, weights=None, query_idx=None):
    budget = kib * 1024
    avail = (budget - td.fixed - cache_bytes) * 8
    w = td.v + 1.0 if weights is None else weights
    M = float(avail)
    for _ in range(20):
        b, f, e = D.allocate(td.g, w, M)
        reg_seg, n, bpm, m, kind = E5.region_bits(td, b, f)
        if m.sum() <= avail:
            break
        M *= avail / m.sum() * 0.9999
    k = np.where(kind == C.BF, np.maximum(1, np.rint(bpm * np.log(2))), 0).astype(np.int64)
    off = np.concatenate([[0], np.cumsum(m)]).astype(np.int64)
    bits = np.zeros((int(off[-1]) + 7) // 8, np.uint8)
    R.packed_build(setup.h1m, reg_seg[td.seg_m].astype(np.int32), off, m, k, bits)
    flags = R.packed_query(setup.h1q[query_idx], reg_seg[td.seg_q[query_idx]].astype(np.int32), kind, off, m, k, bits)
    return bits, flags, e


def point(setup, scores, safe, trees, fracs, L, pool):
    budget = KIB * 1024
    spec = ('zipf', pool, S_ZIPF)
    base = E5.base_stream(setup, f'zipf{S_ZIPF}', spec, 0, queries=4 * L)
    n = len(base) // 4
    learn, tail = base[:n], base[n:]
    keys = np.unique(learn)
    learn_local = np.searchsorted(keys, learn).astype(np.int64)
    h_local, safe_local = setup.h1q[keys], safe[keys]
    freq_local = np.bincount(learn_local, minlength=len(keys))
    tds = {t: E5.tree(setup, scores, t) for t in trees}
    trees = [t for t in trees if tds[t].fixed < budget]

    def grid():
        order, best = [], None
        for t in trees:
            for f in fracs:
                cb, S = E5.cache_alloc(budget, f)
                if (budget - tds[t].fixed - cb) * 8 <= 0:
                    continue
                bits, flags, e = dp_bf(setup, tds[t], KIB, cb, query_idx=keys)
                del bits
                order.append((e, t, f, cb, flags))
        order.sort(key=lambda r: r[:3])
        for e, t, f, cb, flags in order:
            lim = best[0] if best else 2 ** 62
            if cb == 0:
                v, cut = int(freq_local[flags].sum()), False
            else:
                r = K.simulate(learn_local, h_local, safe_local, flags, cb, E5.PREFIX, E5.WAYS, limit=lim)
                v, cut = r['fp'], bool(r['cutoff'])
            if not cut and (best is None or (v, e, t, f) < best):
                best = (v, e, t, f)
        return best[2], best[3], len(order)

    def ra6_sel():
        lm = RA.ra4.summarize(learn, True)
        H = len(tail)
        table = RA.candidate_table(setup, scores, lm, KIB, H, RA.Config(new_mix=0.), fracs=fracs, trees=trees)
        short = sorted(table, key=lambda r: (r['pred'], r['trees'], r['frac']))[:ra6.TOPK]
        best = None
        for rank, row in enumerate(short):
            td = tds[row['trees']]
            bits, flags, _ = dp_bf(setup, td, KIB, row['cache_bytes'], weights=row['weights'], query_idx=lm.keys)
            lam = lm.rate[flags]
            G = H * lm.N1 / lm.L * td.h
            new_miss = float((row['seg_fpr_pred'] * G).sum())
            if row['cache_bytes'] == 0:
                pred = float((lam * H).sum()) + new_miss
            else:
                B = row['slots'] // ra6.WAYS
                pred = ra6.bucket_che(lam, ra6.buckets_of(setup.h1q[lm.keys[flags]], B), B, H, new_miss / H / B) + new_miss
            if best is None or (pred, rank) < best[0]:
                best = ((pred, rank), row)
        return best[1]['trees'], best[1]['frac'], best[1]['weights'], len(table)

    res = dict(trees=len(trees), fracs=len(fracs), L=int(n), pool=pool or len(setup.h1q), distinct_learning_keys=int(len(keys)))
    for name, fn in (('LearnGrid', grid), ('RA6', ra6_sel)):
        fn()                                           # warm-up
        ts = []
        for _ in range(REPS):
            t0 = time.perf_counter()
            out = fn()
            ts.append(time.perf_counter() - t0)
        tracemalloc.start()
        fn()
        pk = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        if name == 'LearnGrid':
            c = E5.build(setup, scores, out[0], KIB, out[1])
            state = int(learn.nbytes)
        else:
            cb, S = E5.cache_alloc(budget, out[1])
            c = E5.build(setup, scores, out[0], KIB, out[1], weights=out[2], cache_bytes=cb, slots=S)
            state = int(len(keys) * 16)
        fp = E5.evaluate(c, tail, setup, safe)['fp']
        res[name] = dict(select_s=float(np.median(ts)), select_s_all=ts, peak_bytes=int(pk), state_bytes=state,
                         trees_chosen=int(out[0]), frac_chosen=float(out[1]), candidates=int(out[-1]), fp_tail=int(fp))
    print(json.dumps(res, ensure_ascii=False), flush=True)
    return res


def main(var):
    setup, scores, safe = E5.load(DS)
    dest = ROOT / 'results' / 'e5'
    dest.mkdir(parents=True, exist_ok=True)
    pts = []
    if var == 'candidates':
        for nt, nf in ((6, 5), (6, 10), (12, 20), (12, 40)):
            pts.append(point(setup, scores, safe, tree_grid(nt), frac_grid(nf), 2_500_000, None))
    elif var == 'learning':
        for L in (100_000, 1_000_000, 10_000_000):
            pts.append(point(setup, scores, safe, ALL_TREES, frac_grid(13), L, None))
    elif var == 'keys':
        for pool in (10_000, 100_000, 1_000_000, None):
            pts.append(point(setup, scores, safe, ALL_TREES, frac_grid(13), 2_500_000, pool))
    (dest / f'{var}.json').write_text(json.dumps(pts, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1])

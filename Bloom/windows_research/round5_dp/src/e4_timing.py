"""E4: build-time breakdown with one accounting for every method (single thread, JIT excluded).

Stages (seconds; selection and build: median of 5 runs after a warm-up run):
  train   200 trees once (LightGBM, num_threads=1; shared by all methods, measured once)
  score   members + validation for every tree count (all methods);
          distinct learning-period keys for every tree count (grid and RA4 only)
  select  Gama:     FastPLBF DP per tree count -> est FPR
          LearnGrid: build every candidate (DP + Bloom insert + query the distinct learning keys)
                     + exact replay of the learning period (early stopping as in round 5)
          RA4:      learning statistics + candidate table (ra5.select)
          RA4-fast: same with ra5fast.select_fast (DP only for the 10 best closed-form candidates;
                    NOT equivalent to RA4 on 49/956 cases, reported for reference only)
          RA6:      RA4 candidate table + build the 5 best (DP + Bloom insert + query the distinct
                    learning keys) + per-bucket Che from the actual bucket load (round 6)
          FastPLBF48: one DP
  build   the selected structure: DP + Bloom insert (cache array allocation included)
Memory: tracemalloc peak during selection (separate run); for the grid also the analytic size of
all candidates held at once ('materialized') vs one at a time ('streaming').
usage: e4_timing.py <dataset> <budget_kib> [workload]
"""
import os
for _v in ('NUMBA_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import tracemalloc  # noqa: E402
from pathlib import Path  # noqa: E402
import numpy as np  # noqa: E402
import lightgbm as lgb  # noqa: E402
import engine5 as E5  # noqa: E402
import ra5 as RA  # noqa: E402
import ra5fast as RF  # noqa: E402
import dp_alloc as D  # noqa: E402
import cache5 as K  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'round6_bucket' / 'src'))
import ra6 as R6  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R, C = E5.R, E5.C
REPS = 5


def med(f, reps=REPS):
    f()                                   # warm-up (JIT, caches)
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        out = f()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts)), out


def peak(f):
    tracemalloc.start()
    f()
    p = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return p


def dp_bf(setup, td, kib, cache_bytes, weights=None, query_idx=None):
    """DP + Bloom insert (+ optional query of selected pool keys). Returns bits, flags."""
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
    cache = K.allocate(K.layout(cache_bytes)) if cache_bytes else None
    flags = None
    if query_idx is not None:
        flags = R.packed_query(setup.h1q[query_idx], reg_seg[td.seg_q[query_idx]].astype(np.int32), kind, off, m, k, bits)
    return bits, flags, e, cache


def main(ds, kib, workload):
    setup, scores, safe = E5.load(ds)
    budget = kib * 1024
    spec = None if ds.endswith('_flow') else dict(E5.workload_specs(len(setup.h1q)))[workload]
    name = '真实轨迹' if ds.endswith('_flow') else workload
    base = E5.base_stream(setup, name, spec, 0)
    n = len(base) // 4
    learn = base[:n]
    keys = np.unique(learn)
    trees = [t for t in E5.TREES if E5.tree(setup, scores, t).fixed < budget]
    out = dict(dataset=ds, budget_kib=kib, workload=name, learning_queries=n, distinct_learning_keys=len(keys))

    # ---- train (once) and score
    ids, y, X, feats = C.load_dataset(ds)
    sp = C.make_split(ids, y, ds)
    tr = sp['member_train'] | sp['neg_train']
    t0 = time.perf_counter()
    booster = lgb.train(dict(objective='binary', num_leaves=31, learning_rate=.1, num_threads=1, verbose=-1, seed=1,
                             deterministic=True, force_col_wise=True), lgb.Dataset(X[tr], label=y[tr]), num_boost_round=200)
    out['t_train_s'] = time.perf_counter() - t0
    Xmv = X[y | sp['neg_val']]
    Xl = X[np.flatnonzero(sp['neg_test'])[keys]]
    out['t_score_members_val_s'] = med(lambda: [booster.predict(Xmv, raw_score=True, num_iteration=t, num_threads=1) for t in trees], 1)[0]
    out['t_score_learning_keys_s'] = med(lambda: [booster.predict(Xl, raw_score=True, num_iteration=t, num_threads=1) for t in trees], 1)[0]

    # ---- per-method selection
    tds = {t: E5.tree(setup, scores, t) for t in trees}

    def gama_select():
        return min((D.allocate(tds[t].g, tds[t].v + 1.0, float((budget - tds[t].fixed) * 8))[2], t) for t in trees)[1]

    def grid_select(hold=True):
        held, best = [], None
        freq = np.bincount(learn, minlength=len(setup.h1q))
        order = []
        for t in trees:
            for f in E5.FRACS:
                cb, S = E5.cache_alloc(budget, f)
                if (budget - tds[t].fixed - cb) * 8 <= 0:
                    continue
                bits, flags, e, _ = dp_bf(setup, tds[t], kib, cb, query_idx=keys)
                fp = np.zeros(len(setup.h1q), np.bool_)
                fp[keys] = flags
                order.append((e, t, f, cb, fp))
                if hold:
                    held.append((bits, flags))
        order.sort(key=lambda r: r[:3])
        for e, t, f, cb, fp in order:
            lim = best[0] if best else 2 ** 62
            if cb == 0:
                v, cut = int(freq[fp].sum()), False
            else:
                r = K.simulate(learn, setup.h1q, safe, fp, cb, E5.PREFIX, E5.WAYS, limit=lim)
                v, cut = r['fp'], bool(r['cutoff'])
            if not cut and (best is None or (v, e, t, f) < best):
                best = (v, e, t, f)
        held_bytes = sum(b.nbytes + fl.nbytes for b, fl in held)
        return best[2], best[3], held_bytes, max((b.nbytes + fl.nbytes for b, fl in held), default=0)

    def ra_select():
        lm = RA.ra4.summarize(learn, True)
        table = RA.candidate_table(setup, scores, lm, kib, len(base) - n, RA.Config(new_mix=0.))
        b = min(table, key=lambda r: (r['pred'], r['trees'], r['frac']))
        return b['trees'], b['frac'], b['weights'], b['cache_bytes']

    def ra6_select():
        lm = RA.ra4.summarize(learn, True)
        H = len(base) - n
        table = RA.candidate_table(setup, scores, lm, kib, H, RA.Config(new_mix=0.))
        short = sorted(table, key=lambda r: (r['pred'], r['trees'], r['frac']))[:R6.TOPK]
        best = None
        for rank, row in enumerate(short):
            td = tds[row['trees']]
            bits, flags, _, _ = dp_bf(setup, td, kib, row['cache_bytes'], weights=row['weights'], query_idx=lm.keys)
            lam = lm.rate[flags]
            G = H * lm.N1 / lm.L * td.h
            new_miss = float((row['seg_fpr_pred'] * G).sum())
            if row['cache_bytes'] == 0:
                pred = float((lam * H).sum()) + new_miss
            else:
                B = row['slots'] // R6.WAYS
                b = R6.buckets_of(setup.h1q[lm.keys[flags]], B)
                pred = R6.bucket_che(lam, b, B, H, new_miss / H / B) + new_miss
            if best is None or (pred, rank) < best[0]:
                best = ((pred, rank), row)
        return best[1]['trees'], best[1]['frac']

    def ra_fast_select():
        lm = RA.ra4.summarize(learn, True)
        c, info = RF.select_fast(setup, scores, lm, kib, len(base) - n, RA.Config(new_mix=0.))
        return info['trees'], info['frac']

    res = {}
    s, gt = med(gama_select)
    res['Gama'] = dict(select_s=s, build_s=med(lambda: dp_bf(setup, tds[gt], kib, 0))[0], trees=gt)
    s, (t48) = med(lambda: D.allocate(tds[48].g, tds[48].v + 1.0, float((budget - tds[48].fixed) * 8)) if 48 in tds else None)
    if 48 in tds:
        res['FastPLBF48'] = dict(select_s=s, build_s=med(lambda: dp_bf(setup, tds[48], kib, 0))[0], trees=48)
    s, g = med(lambda: grid_select(True), 3)
    res['LearnGrid'] = dict(select_s=s, trees=g[0], frac=g[1], held_candidate_bytes=g[2], one_candidate_bytes=g[3],
                            trace_bytes=learn.nbytes,
                            build_s=med(lambda: dp_bf(setup, tds[g[0]], kib, E5.cache_alloc(budget, g[1])[0]))[0])
    s, rsel = med(ra_select)
    res['RA4'] = dict(select_s=s, trees=rsel[0], frac=rsel[1],
                      build_s=med(lambda: dp_bf(setup, tds[rsel[0]], kib, rsel[3], weights=rsel[2]))[0])
    s, r6sel = med(ra6_select, 3)
    res['RA6'] = dict(select_s=s, trees=r6sel[0], frac=r6sel[1], build_s=0.0,
                      note='the chosen structure is one of the 5 already built during selection')
    s, fsel = med(ra_fast_select)
    res['RA4-fast'] = dict(select_s=s, trees=fsel[0], frac=fsel[1], same_choice_as_RA4=(fsel[0], fsel[1]) == (rsel[0], rsel[1]))
    # memory peaks during selection (separate runs)
    res['Gama']['select_peak_bytes'] = peak(gama_select)
    res['LearnGrid']['select_peak_bytes_materialized'] = peak(lambda: grid_select(True))
    res['LearnGrid']['select_peak_bytes_streaming'] = peak(lambda: grid_select(False))
    res['RA4']['select_peak_bytes'] = peak(ra_select)
    res['RA4-fast']['select_peak_bytes'] = peak(ra_fast_select)
    res['RA6']['select_peak_bytes'] = peak(ra6_select)
    out['methods'] = res
    out['hardware'] = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip()
    out['threads'] = 1
    dest = ROOT / 'results' / 'e4'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f'{ds}_{kib}.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 'zipf1.0-全部')

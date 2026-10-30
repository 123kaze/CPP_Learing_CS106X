"""E7 query latency/throughput, E8 end-to-end with SQLite, E9 cold start -- round-6 selections.

Methods, each with the structure it selects on the learning period of the negative stream
(exactly as in the round-5/6 main tables; checked against their rows):
  FastPLBF48, Gama (no cache), Gama+10%, LearnGrid, RA6.
Learned stacked and SkiQF-style admission live in other engines (round 2) and are not timed here.

Query path (numba, one thread): cache probe (cache5, arbitrary buckets) -> on a miss, traversal of
the compact model arrays on the query key's features -> DP region -> packed Bloom probes; a false
positive inserts its verified prefix (binary search in the sorted member hashes) into the cache.
Consistency checks (asserted): traversal scores equal LightGBM's raw scores; every member is
accepted; the pool-wide FP flags equal the structure's fp_static; E9's FP total on the negative
tail equals the main-table fp_tail of the same method and stream.

  E7  stream = negatives with members mixed in at 10% / 50%; the end of the learning period warms
      up, then TIMED queries are timed in chunks of CHUNK (perf_counter_ns around each numba call).
      Reported: mean ns/query, p50/p99 of chunk means, Mqps; stage split from three modes
      (model only / model + Bloom / full).  Median of REPS runs.
  E8  same mixed stream (10%), SQLITE_Q queries: every accepted query is a real SQLite point read
      (file-backed and in-memory DB of the members); NoFilter reads for every query.  A remote
      backend is a projection: measured time + backend_calls x {50, 500} us.
  E9  the whole negative evaluation segment (cold cache), cut into WINDOWS windows: FP and cache
      hits per window; steady state = first window after which the windowed FPR stays within
      +-10% of its final-quarter mean.
usage: e789.py <dataset> <budget_kib> [workload]  -> results/e789/<ds>_<kib>.json
"""
import os
for _v in ('NUMBA_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_v] = '1'
import json  # noqa: E402
import sqlite3  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
import csv  # noqa: E402
from pathlib import Path  # noqa: E402
import numpy as np  # noqa: E402
import lightgbm as lgb  # noqa: E402
from numba import njit  # noqa: E402
import ra6  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R5 = ROOT.parent / 'round5_dp' / 'results'
E5, RA = ra6.E5, ra6.RA
K, D, R, C = E5.K, E5.D, E5.R, E5.C
PASS, BF = int(C.PASS), int(C.BF)
CHUNK = 1000
TIMED = 1_500_000
WARM = 500_000
REPS = 3
WINDOWS = 100
SQLITE_Q = 200_000
POS = (0.1, 0.5)


@njit(cache=True)
def scores_numba(Xrows, idx, feat, thr, left, right, leaf, roots):
    out = np.empty(len(idx))
    for i in range(len(idx)):
        x = Xrows[idx[i]]
        s = 0.0
        for root in roots:
            n = np.int64(root)
            while n >= 0:
                n = np.int64(left[n] if x[feat[n]] <= thr[n] else right[n])
            s += leaf[~n]
        out[i] = s
    return out


@njit(cache=True)
def safe_len(sorted_m, h):
    i = np.searchsorted(sorted_m, h)
    best = 1
    for j in (i - 1, i):
        if 0 <= j < len(sorted_m):
            x = sorted_m[j] ^ h
            if x == 0:
                return 65
            lz = 0
            b = np.uint64(1) << np.uint64(63)
            while (x & b) == 0:
                lz += 1
                b >>= np.uint64(1)
            best = max(best, lz + 1)
    return best


@njit(cache=True)
def step(stream, lo, hi, Xrows, hashes, member, feat, thr, left, right, leaf, roots, raw_cuts, reg_of_seg,
         kind, off, m, k, bits, sorted_m, data, B, P, Q, ob, sb, ways, hb, mode, cnt, acc_out, fp_win, hit_win,
         win_lo, win_n):
    """Process stream[lo:hi]. mode 0 model only, 1 model + Bloom, 2 full.
    cnt: accepted, FP, member FN, cache hits, model calls, dummy.  acc_out[i]=1 if query i accepted."""
    for i in range(lo, hi):
        x = stream[i]
        h = hashes[x]
        hit = False
        if mode == 2 and B > 0:
            hit = K.lookup(data, h, B, P, Q, ob, sb, ways)
        if hit:
            cnt[3] += 1
            if win_n > 0 and i >= win_lo:
                hit_win[(i - win_lo) * len(hit_win) // win_n] += 1
            continue
        cnt[4] += 1
        xr = Xrows[x]
        s = 0.0
        for root in roots:
            n = np.int64(root)
            while n >= 0:
                n = np.int64(left[n] if xr[feat[n]] <= thr[n] else right[n])
            s += leaf[~n]
        if mode == 0:
            cnt[5] += np.int64(s > 0)
            continue
        g = reg_of_seg[max(np.searchsorted(raw_cuts, s, side='left'), 1) - 1]
        ok = False
        if kind[g] == PASS:
            ok = True
        elif kind[g] == BF:
            ok = True
            for j in range(k[g]):
                p = off[g] + C.bf_pos(h, j, m[g])
                if (bits[p >> 3] >> (p & 7)) & 1 == 0:
                    ok = False
                    break
        if ok:
            cnt[0] += 1
            acc_out[i - lo] = 1
            if not member[x]:
                cnt[1] += 1
                if win_n > 0 and i >= win_lo:
                    fp_win[(i - win_lo) * len(fp_win) // win_n] += 1
                if mode == 2 and B > 0:
                    K.insert(data, h, safe_len(sorted_m, h), B, P, Q, ob, sb, ways, hb)
        elif member[x]:
            cnt[2] += 1


class Exe:
    """Executable structure: model arrays, raw-score cut points, packed Bloom, cache layout."""

    def __init__(self, setup, scores, c, space):
        st = c['structure']
        t = c['trees']
        td = E5.tree(setup, scores, t)
        arrays = R._MODEL_ARRAYS[setup.name, t]
        self.model = tuple(np.ascontiguousarray(arrays[k_]) for k_ in ('feat', 'thr', 'left', 'right', 'leaf', 'roots'))
        reg_seg = D.region_of_segment(st.b)
        self.reg_of_seg = reg_seg.astype(np.int64)
        # rebuild the packed bits exactly as engine5.build does (deterministic)
        off = np.concatenate([[0], np.cumsum(st.m)]).astype(np.int64)
        bits = np.zeros((int(off[-1]) + 7) // 8, np.uint8)
        R.packed_build(setup.h1m, reg_seg[td.seg_m].astype(np.int32), off, st.m, st.k, bits)
        assert bits.nbytes == st.filter_bytes
        self.kind, self.off, self.m, self.k, self.bits = st.kind.astype(np.int64), off, st.m, st.k, bits
        # raw-score cut points: segment = max(searchsorted(raw_cuts, raw, 'left'), 1) - 1, matching
        # D.segment_of(sigmoid(raw)); boundary agreement is verified on every key below.
        e = D.edges()
        with np.errstate(divide='ignore'):
            self.raw_cuts = np.log(e) - np.log1p(-e)
        self.cache_bytes = c['cache_bytes']
        self.spec = K.layout(self.cache_bytes) if self.cache_bytes else dict(buckets=0, Q=32, ob=0, slot_bits=0, handbits=0, nwords=0)
        self.space = space
        self.c = c

    def fresh_cache(self):
        return K.allocate(self.spec) if self.cache_bytes else np.zeros(1, np.uint64)

    def run(self, stream, lo, hi, mode, data, acc=None, fp_win=None, hit_win=None, win_lo=0, win_n=0):
        s = self.space
        cnt = np.zeros(6, np.int64)
        acc = np.zeros(hi - lo, np.uint8) if acc is None else acc
        fw = np.zeros(1, np.int64) if fp_win is None else fp_win
        hw = np.zeros(1, np.int64) if hit_win is None else hit_win
        sp = self.spec
        step(stream, lo, hi, s.X, s.h, s.member, *self.model, self.raw_cuts, self.reg_of_seg, self.kind, self.off,
             self.m, self.k, self.bits, s.sorted_m, data, sp['buckets'], E5.PREFIX, sp['Q'], sp['ob'], sp['slot_bits'],
             E5.WAYS, sp['handbits'], mode, cnt, acc, fw, hw, win_lo, win_n)
        return cnt, acc


def space_of(setup, ds):
    """Index space: 0..Nm-1 members, Nm.. pool negatives (neg_test order)."""
    _, y, X, _ = C.load_dataset(ds)
    sp = setup.split
    Xm, Xq = X[y], X[sp['neg_test']]
    from types import SimpleNamespace
    s = SimpleNamespace(X=np.ascontiguousarray(np.vstack([Xm, Xq]).astype(np.float32)),
                        h=np.concatenate([setup.h1m, setup.h1q]).astype(np.uint64),
                        member=np.concatenate([np.ones(len(Xm), np.bool_), np.zeros(len(Xq), np.bool_)]),
                        sorted_m=np.sort(setup.h1m).astype(np.uint64), nm=len(Xm), nq=len(Xq),
                        ids=np.concatenate([setup.ids[y], setup.q_ids]).astype(np.uint64))
    return s


def verify(exe, setup, scores, space, ds):
    """Scores, member acceptance and pool FP flags of the executable path."""
    t = exe.c['trees']
    raw = scores[t]
    _, y, _, _ = C.load_dataset(ds)
    ref = np.concatenate([raw[y], raw[setup.split['neg_test']]])
    idx = np.arange(space.nm + space.nq)
    got = scores_numba(space.X, idx, *exe.model)
    assert np.max(np.abs(got - ref)) < 1e-9, ('traversal != LightGBM', float(np.max(np.abs(got - ref))))
    seg_py = np.concatenate([E5.tree(setup, scores, t).seg_m, E5.tree(setup, scores, t).seg_q])
    seg_nb = np.maximum(np.searchsorted(exe.raw_cuts, got, side='left'), 1) - 1
    mism = int((seg_py != seg_nb).sum())
    data = np.zeros(1, np.uint64)
    cnt, acc = exe.run(idx.astype(np.int64), 0, len(idx), 1, data)
    assert cnt[2] == 0, 'member false negative'
    assert np.array_equal(acc[space.nm:].astype(bool), exe.c['structure'].fp_static), 'pool FP flags differ'
    return mism


def select_all(setup, scores, safe, kib, learn, H):
    cands = E5.candidates(setup, scores, kib)
    by = {(c['trees'], c['frac']): c for c in cands}
    gama = E5.gama(cands)
    grid, _ = E5.replay_best(cands, learn, setup, safe)
    lm = RA.ra4.summarize(learn, True)
    ra, info = ra6.select6(setup, scores, lm, kib, H)
    return {'FastPLBF48': by.get((48, 0.)), 'Gama': gama, 'Gama+10%': by.get((gama['trees'], .1)),
            'LearnGrid': grid, 'RA6': ra}


def main_rows(ds, kib, workload):
    out = {}
    for f, tag in ((R5 / f'rows_{ds}_{kib}.csv', 5), (ROOT / 'results' / 'main' / f'rows_{ds}_{kib}.csv', 6)):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r['workload'] == workload and r['seed'] == '0':
                out[r['method']] = r
    return out


def mixed(neg, nm, frac, rng):
    """Negative pool indices shifted to the joint space, members mixed in at `frac`."""
    s = neg.astype(np.int64) + nm
    pick = rng.random(len(s)) < frac
    s[pick] = rng.integers(0, nm, int(pick.sum()))
    return s


def main(ds, kib, workload):
    setup, scores, safe = E5.load(ds)
    real = ds.endswith('_flow')
    workload = '真实轨迹' if real else workload
    spec = None if real else dict(E5.workload_specs(len(setup.h1q)))[workload]
    base = E5.base_stream(setup, workload, spec, 0)
    n = len(base) // 4
    learn, tail = base[:n], base[n:]
    space = space_of(setup, ds)
    sel = select_all(setup, scores, safe, kib, learn, len(tail))
    rows = main_rows(ds, kib, workload)
    res = dict(dataset=ds, budget_kib=kib, workload=workload, members=space.nm, pool=space.nq,
               hardware=subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip(),
               methods={})
    exes = {}
    for name, c in sel.items():
        if c is None:
            continue
        exe = Exe(setup, scores, c, space)
        mism = verify(exe, setup, scores, space, ds)
        exes[name] = exe
        # E9 + consistency with the main table
        data = exe.fresh_cache()
        fw, hw = np.zeros(WINDOWS, np.int64), np.zeros(WINDOWS, np.int64)
        st = (tail.astype(np.int64) + space.nm)
        cnt, _ = exe.run(st, 0, len(st), 2, data, fp_win=fw, hit_win=hw, win_lo=0, win_n=len(st))
        main_fp = int(rows[name]['fp_tail']) if name in rows else None
        assert main_fp is None or int(cnt[1]) == main_fp, (name, int(cnt[1]), main_fp)
        win_q = len(st) / WINDOWS
        fpr = fw / win_q
        final = fpr[3 * WINDOWS // 4:].mean()
        steady = next((w for w in range(WINDOWS) if np.all(np.abs(fpr[w:] - final) <= .1 * max(final, 1e-12))), None)
        res['methods'][name] = dict(trees=c['trees'], cache_bytes=c['cache_bytes'], tail_fp=int(cnt[1]), main_table_fp=main_fp,
                                    segment_boundary_mismatches=mism,
                                    e9=dict(fp_per_window=fw.tolist(), hits_per_window=hw.tolist(), window_queries=win_q,
                                            steady_window=steady, steady_queries=None if steady is None else int(steady * win_q)))
        print(ds, kib, name, 'verified; tail FP', int(cnt[1]), 'main', main_fp, 'boundary mismatches', mism, flush=True)

    rng = np.random.default_rng(7)
    neg_slice = base[n - WARM: n + TIMED]
    for frac in POS:
        st = mixed(neg_slice, space.nm, frac, rng)
        for name, exe in exes.items():
            out = {}
            for mode, label in ((0, 'model'), (1, 'model+bf'), (2, 'full')):
                if frac != POS[0] and mode != 2:
                    continue
                runs = []
                for rep in range(REPS + 1):
                    data = exe.fresh_cache()
                    exe.run(st, 0, WARM, mode, data)             # warm-up (also JIT on the first call)
                    ts = []
                    for lo in range(WARM, len(st), CHUNK):
                        hi = min(lo + CHUNK, len(st))
                        t0 = time.perf_counter_ns()
                        exe.run(st, lo, hi, mode, data)
                        ts.append((time.perf_counter_ns() - t0) / (hi - lo))
                    if rep:
                        runs.append(ts)
                ts = np.array(runs)
                mean = float(np.median(ts.mean(axis=1)))
                out[label] = dict(ns_mean=mean, ns_p50_chunk=float(np.median(np.median(ts, axis=1))),
                                  ns_p99_chunk=float(np.median(np.quantile(ts, .99, axis=1))), mqps=1e3 / mean)
            res['methods'][name].setdefault('e7', {})[f'pos{int(frac * 100)}'] = out
            print(ds, kib, name, f'pos{frac}', {k_: round(v['ns_mean'], 1) for k_, v in out.items()}, flush=True)

    # E8: SQLite point reads for accepted queries
    st = mixed(base[n: n + SQLITE_Q], space.nm, POS[0], np.random.default_rng(8))
    with tempfile.TemporaryDirectory() as tmp:
        for variant in ('file', 'memory'):
            path = os.path.join(tmp, 'kv.sqlite') if variant == 'file' else ':memory:'
            con = sqlite3.connect(path)
            con.execute('CREATE TABLE kv (key INTEGER PRIMARY KEY, value BLOB NOT NULL)')
            con.executemany('INSERT INTO kv VALUES (?, ?)', ((int(k_), b'\0' * 32) for k_ in space.ids[:space.nm].view(np.int64)))
            con.commit()
            keys = space.ids.view(np.int64)   # the 64-bit key itself as a signed SQLite integer key
            q = 'SELECT value FROM kv WHERE key = ?'
            for _ in range(2000):
                con.execute(q, (int(keys[0]),)).fetchone()
            e8 = {}
            for name in ['NoFilter'] + list(exes):
                times, calls, found = [], 0, 0
                for rep in range(REPS):
                    exe = exes.get(name)
                    data = exe.fresh_cache() if exe else None
                    t0 = time.perf_counter_ns()
                    if exe:
                        _, acc = exe.run(st, 0, len(st), 2, data)
                        hit_idx = np.flatnonzero(acc)
                    else:
                        hit_idx = np.arange(len(st))
                    cur = con.cursor()
                    f_ = 0
                    for i in hit_idx:
                        f_ += cur.execute(q, (int(keys[st[i]]),)).fetchone() is not None
                    times.append(time.perf_counter_ns() - t0)
                    calls, found = len(hit_idx), f_
                t = float(np.median(times)) / len(st)
                e8[name] = dict(ns_per_query=t, backend_calls=calls, members_found=found,
                                projected_us_per_query={'50us': t / 1e3 + calls * 50 / len(st), '500us': t / 1e3 + calls * 500 / len(st)})
            res.setdefault('e8', {})[variant] = e8
            print(ds, kib, 'E8', variant, {k_: (round(v['ns_per_query']), v['backend_calls']) for k_, v in e8.items()}, flush=True)
            con.close()
    dest = ROOT / 'results' / 'e789'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f'{ds}_{kib}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 'zipf1.0-全部')

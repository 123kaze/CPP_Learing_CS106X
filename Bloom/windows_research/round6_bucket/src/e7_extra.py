"""E7 supplement: query cost of learned stacked and SkiQF-style two-hit admission.

Both baselines are expressed on the round-5 engine (DP allocator, packed Bloom, cache5) so that
the timed query path is the same numba code as the other methods; selection is done on the
learning period exactly like the round-2 versions, with the round-5 candidate fractions:
  learned stacked:  Gama's tree count; base PLBF with `frac` of the budget moved to two side
                    layers (negative BF of the learning-period FPs, then a positive BF of the
                    members that the negative BF hits); frac x b2 chosen on the second half of the
                    learning period (round-2 protocol).  Query: model -> region Bloom; if
                    accepted, negative BF; if it hits, positive BF decides.
  SkiQF admission:  RA6's structure; on a false positive the key is admitted into the cache only
                    if it was seen in the 256-entry probation table (second hit).  The probation
                    table (256 x 9 bytes + 2 array headers) is charged inside the cache budget.
Timed exactly like e789 (chunks of CHUNK, warm-up, median of REPS); tail FP on the negative stream
is reported, and the timing JSON is merged into results/e789/<ds>_<kib>.json under 'e7_extra'.
usage: e7_extra.py <dataset> <budget_kib> [workload]
"""
import os
for _v in ('NUMBA_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_v] = '1'
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
import numpy as np  # noqa: E402
from numba import njit  # noqa: E402
import e789 as X  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
E5, RA, K, D, R, C, ra6 = X.E5, X.RA, X.K, X.D, X.R, X.C, X.ra6
PASS, BF = X.PASS, X.BF
FRACS = (.02, .05, .1, .2, .4, .6)
B2S = (.5, 1, 2, 4, 6, 8, 12)
PROB = 256
PROB_BYTES = PROB * 9 + 2 * K.ARRAY_HEADER


def bf_build(h, nbytes, k):
    m = np.array([nbytes * 8], np.int64)
    bits = np.zeros(nbytes, np.uint8)
    R.packed_build(h, np.zeros(len(h), np.int32), np.array([0, nbytes * 8], np.int64), m, np.array([k], np.int64), bits)
    return bits


def bf_query(h, bits, k):
    return R.packed_query(h, np.zeros(len(h), np.int32), np.array([C.BF], np.uint8), np.array([0, len(bits) * 8], np.int64),
                          np.array([len(bits) * 8], np.int64), np.array([k], np.int64), bits)


def stacked_layers(setup, base, known, side, b2):
    over = 2 * K.ARRAY_HEADER + 64
    n2 = max(1, (int(b2 * len(known)) + 7) // 8)
    n3 = side - over - n2
    if len(known) == 0 or n3 < 1:
        return None
    k2 = max(1, round(b2 * np.log(2)))
    neg = bf_build(setup.h1q[known], n2, k2)
    hit = bf_query(setup.h1m, neg, k2)
    k3 = max(1, min(32, round(n3 * 8 / max(1, int(hit.sum())) * np.log(2))))
    pos = bf_build(setup.h1m[hit], n3, k3)
    nq = bf_query(setup.h1q, neg, k2)
    pq = bf_query(setup.h1q, pos, k3)
    return dict(neg=neg, k2=k2, pos=pos, k3=k3, fp=base['structure'].fp_static & (~nq | pq), side=n2 + n3 + over)


def choose_stacked(setup, scores, kib, gama_t, learn):
    split = len(learn) // 2
    counts = np.bincount(learn[split:], minlength=len(setup.h1q))
    g = E5.build(setup, scores, gama_t, kib, 0.)
    best = (int(counts[g['structure'].fp_static].sum()), 0., 0.)
    for f in FRACS:
        side = int(kib * 1024 * f)
        base = E5.build(setup, scores, gama_t, kib, 0., cache_bytes=side, slots=0)
        if base is None:
            continue
        fl = base['structure'].fp_static
        known = np.unique(learn[:split][fl[learn[:split]]])
        for b2 in B2S:
            L = stacked_layers(setup, base, known, side, b2)
            if L is None:
                continue
            v = int(counts[L['fp']].sum())
            if (v, f, b2) < best:
                best = (v, f, b2)
    _, f, b2 = best
    if f == 0:
        return g, None
    side = int(kib * 1024 * f)
    base = E5.build(setup, scores, gama_t, kib, 0., cache_bytes=side, slots=0)
    fl = base['structure'].fp_static
    L = stacked_layers(setup, base, np.unique(learn[fl[learn]]), side, b2)
    if L is None:                       # round-2 behaviour: layers no longer fit -> Gama
        return g, None
    L.update(frac=f, b2=b2)
    return base, L


@njit(cache=True)
def step_stacked(stream, lo, hi, Xrows, hashes, member, feat, thr, left, right, leaf, roots, raw_cuts, reg_of_seg,
                 kind, off, m, k, bits, neg, k2, pos, k3, has_side, cnt):
    m2, m3 = np.int64(len(neg)) * 8, np.int64(len(pos)) * 8
    for i in range(lo, hi):
        x = stream[i]
        h = hashes[x]
        xr = Xrows[x]
        s = 0.0
        for root in roots:
            n = np.int64(root)
            while n >= 0:
                n = np.int64(left[n] if xr[feat[n]] <= thr[n] else right[n])
            s += leaf[~n]
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
        if ok and has_side:
            nh = True
            for j in range(k2):
                p = C.bf_pos(h, j, m2)
                if (neg[p >> 3] >> (p & 7)) & 1 == 0:
                    nh = False
                    break
            if nh:
                ph = True
                for j in range(k3):
                    p = C.bf_pos(h, j, m3)
                    if (pos[p >> 3] >> (p & 7)) & 1 == 0:
                        ph = False
                        break
                ok = ph
        if ok:
            cnt[0] += 1
            if not member[x]:
                cnt[1] += 1
        elif member[x]:
            cnt[2] += 1


@njit(cache=True)
def step_ski(stream, lo, hi, Xrows, hashes, member, feat, thr, left, right, leaf, roots, raw_cuts, reg_of_seg,
             kind, off, m, k, bits, sorted_m, data, B, P, Q, ob, sb, ways, hb, prob, valid, cnt):
    for i in range(lo, hi):
        x = stream[i]
        h = hashes[x]
        if B > 0 and K.lookup(data, h, B, P, Q, ob, sb, ways):
            cnt[3] += 1
            continue
        xr = Xrows[x]
        s = 0.0
        for root in roots:
            n = np.int64(root)
            while n >= 0:
                n = np.int64(left[n] if xr[feat[n]] <= thr[n] else right[n])
            s += leaf[~n]
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
            if not member[x]:
                cnt[1] += 1
                slot = np.int64(h % np.uint64(len(prob)))
                if valid[slot] and prob[slot] == h:
                    if B > 0:
                        K.insert(data, h, X.safe_len(sorted_m, h), B, P, Q, ob, sb, ways, hb)
                prob[slot] = h
                valid[slot] = True
        elif member[x]:
            cnt[2] += 1


def timed(fn, st):
    runs = []
    for rep in range(X.REPS + 1):
        ctx = fn.fresh()
        fn(st, 0, X.WARM, ctx)
        ts = []
        for lo in range(X.WARM, len(st), X.CHUNK):
            hi = min(lo + X.CHUNK, len(st))
            t0 = time.perf_counter_ns()
            fn(st, lo, hi, ctx)
            ts.append((time.perf_counter_ns() - t0) / (hi - lo))
        if rep:
            runs.append(ts)
    ts = np.array(runs)
    mean = float(np.median(ts.mean(axis=1)))
    return dict(ns_mean=mean, ns_p50_chunk=float(np.median(np.median(ts, axis=1))),
                ns_p99_chunk=float(np.median(np.quantile(ts, .99, axis=1))), mqps=1e3 / mean)


def main(ds, kib, workload):
    setup, scores, safe = E5.load(ds)
    real = ds.endswith('_flow')
    workload = '真实轨迹' if real else workload
    spec = None if real else dict(E5.workload_specs(len(setup.h1q)))[workload]
    base = E5.base_stream(setup, workload, spec, 0)
    n = len(base) // 4
    learn, tail = base[:n], base[n:]
    space = X.space_of(setup, ds)
    sel = X.select_all(setup, scores, safe, kib, learn, len(tail))
    out = {}
    # ---- learned stacked
    gt = sel['Gama']['trees']
    sb_base, L = choose_stacked(setup, scores, kib, gt, learn)
    exe = X.Exe(setup, scores, sb_base, space)
    exe.cache_bytes = 0          # the reserved bytes hold the two side Bloom layers, not a cache
    if L is None:
        neg, k2, pos, k3, has = np.zeros(1, np.uint8), 1, np.zeros(1, np.uint8), 1, False
        fp_pool = sb_base['structure'].fp_static
    else:
        neg, k2, pos, k3, has = L['neg'], L['k2'], L['pos'], L['k3'], True
        fp_pool = L['fp']
    used = sb_base['structure'].used_bytes - (L and int(kib * 1024 * L['frac']) or 0) + (L['side'] if L else 0)
    assert used <= kib * 1024

    def fs(st, lo, hi, ctx):
        step_stacked(st, lo, hi, space.X, space.h, space.member, *exe.model, exe.raw_cuts, exe.reg_of_seg, exe.kind, exe.off,
                     exe.m, exe.k, exe.bits, neg, k2, pos, k3, has, ctx)
    fs.fresh = lambda: np.zeros(6, np.int64)
    cnt = fs.fresh()
    idx = np.arange(space.nm + space.nq, dtype=np.int64)
    fs(idx, 0, len(idx), cnt)
    assert cnt[2] == 0, 'stacked false negative'
    tail_fp = int(fp_pool[tail].sum())
    res = dict(trees=gt, frac=L['frac'] if L else 0., b2=L['b2'] if L else 0., used_bytes=int(used), tail_fp=tail_fp)
    rng = np.random.default_rng(7)
    neg_slice = base[n - X.WARM: n + X.TIMED]
    for frac in X.POS:
        st = X.mixed(neg_slice, space.nm, frac, rng)
        res[f'pos{int(frac * 100)}'] = timed(fs, st)
    out['LearnedStacked'] = res
    print(ds, kib, 'LearnedStacked', {k_: (v if not isinstance(v, dict) else round(v['ns_mean'], 1)) for k_, v in res.items()}, flush=True)
    # ---- SkiQF-style two-hit admission on RA6's structure
    c = sel['RA6']
    cache_bytes = max(0, c['cache_bytes'] - PROB_BYTES)
    exe = X.Exe(setup, scores, c, space)
    spec_c = K.layout(cache_bytes) if cache_bytes else dict(buckets=0, Q=32, ob=0, slot_bits=0, handbits=0, nwords=0)

    def fk(st, lo, hi, ctx):
        data, prob, valid, cnt_ = ctx
        step_ski(st, lo, hi, space.X, space.h, space.member, *exe.model, exe.raw_cuts, exe.reg_of_seg, exe.kind, exe.off,
                 exe.m, exe.k, exe.bits, space.sorted_m, data, spec_c['buckets'], E5.PREFIX, spec_c['Q'], spec_c['ob'],
                 spec_c['slot_bits'], E5.WAYS, spec_c['handbits'], prob, valid, cnt_)
    fk.fresh = lambda: (K.allocate(spec_c) if cache_bytes else np.zeros(1, np.uint64), np.zeros(PROB, np.uint64),
                        np.zeros(PROB, np.bool_), np.zeros(6, np.int64))
    ctx = fk.fresh()
    st = (tail.astype(np.int64) + space.nm)
    fk(st, 0, len(st), ctx)
    res = dict(trees=c['trees'], cache_bytes=int(c['cache_bytes']), probation_bytes=PROB_BYTES, tail_fp=int(ctx[3][1]))
    for frac in X.POS:
        st = X.mixed(neg_slice, space.nm, frac, rng)
        res[f'pos{int(frac * 100)}'] = timed(fk, st)
    out['SkiQFAdmission'] = res
    print(ds, kib, 'SkiQFAdmission', {k_: (v if not isinstance(v, dict) else round(v['ns_mean'], 1)) for k_, v in res.items()}, flush=True)
    f = ROOT / 'results' / 'e789' / f'{ds}_{kib}.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    d['e7_extra'] = out
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 'zipf1.0-全部')

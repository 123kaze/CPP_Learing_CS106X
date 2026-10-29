"""Method C, round 4: RA-PLBF with explicit switches for the round-4 diagnosis.

Copy of round3_ra_plbf/src/ra_plbf.py (frozen there). Changes: a `Config` with
  new_mix  share of the unseen-key mass placed like learning singletons (round 3: 0.5;
           round 4 default 0 = all of it like the validation negatives, so that with no
           repeats the weights are exactly PLBF's h and RA-PLBF reduces to PLBF/Gama)
  gt       Good-Turing rates and unseen mass (False: raw c/L rates, no unseen mass)
  setassoc Poisson bucket-load correction for the 4-way cache (False: fully associative Che)
  formula  'enum'  = round-3 solver (enumerate physical cache sizes, consistent T)
           'table' = the design-sheet formula: eps_i = min(1, mu*n_i/(ln2^2*(M_i(T)+mu*b*O_i(T))))
                     with cache memory b*sum eps_i*O_i(T) inside the budget, 1-D search over T,
                     fully associative Che; the cache then gets the largest layout that fits
                     the solved occupancy and the Bloom filters get the rest.
Original round-3 docstring follows.

Method C: repeat-aware per-segment allocation (RA-PLBF).

Learning period -> per score segment i a population of negative keys, each with
an estimated tail query rate, plus a Good-Turing mass of not-yet-seen keys.
The shared cache is modelled with Che's characteristic time T: a key with rate
lam misses on its first tail query and then whenever the gap exceeds T.

  M_i(T): tail misses if segment i were passed directly (eps_i = 1)
  O_i(T): cache slots segment i occupies if passed directly
  BF with FPR eps_i passes a random eps_i share of the keys -> eps_i*M_i, eps_i*O_i

For one physical cache layout with S slots and Bloom bits B:
  min sum_i eps_i*M_i(T)  s.t.  sum_i n_i*ln(1/eps_i)/ln2^2 <= B,  sum_i eps_i*O_i(T) = S
Fixed T gives PLBF's closed form eps_i = min(1, mu*n_i/(ln2^2*M_i(T))), mu bisected
to spend B; T is the largest value whose eps(T) still fits in S slots.  The
cache is WAYS-way set associative, so misses are then corrected with a Poisson
bucket-load model and eps re-solved.  The physical layouts (power-of-two
buckets, exact allocated bytes) and Gama's tree counts are enumerated.
Deployment hands the final weights M_i to the discrete PLBF allocator, so
integer hash counts and PASS/EMPTY kinds are exact.
Without repeats M_i(T) = M_i(0), i.e. PLBF on the learning-period query mass.

Guard (RA-PLBF+G): fit on the first 3/4 of the learning period, replay that
configuration and Gama on the last 1/4; deploy the full-learning RA-PLBF only
if it was not worse there, otherwise Gama.
"""
import sys
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import lightgbm as lgb
from numba import njit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'round2_backlog' / 'src'))
import engine as E  # noqa: E402  (sets the round-2 paths, caches and accounting)
R, C, F = E.R, E.C, E.F
from exp9_fp_stream_controller import fit_stream  # noqa: E402

LN2SQ = np.log(2) ** 2
GT_MAX = 5        # Good-Turing adjusted rates for learning counts <= 5
NEW_MIX = 0.5     # round-3 value; round 4 passes Config.new_mix
PREFIX, WAYS = 40, 4
GUARD_SPLIT = 0.75


class Config:
    def __init__(self, new_mix=0.0, gt=True, setassoc=True, formula='enum', mode='ra', pop='emp'):
        self.new_mix, self.gt, self.setassoc, self.formula, self.mode, self.pop = new_mix, gt, setassoc, formula, mode, pop

    def as_dict(self):
        return dict(new_mix=self.new_mix, gt=self.gt, setassoc=self.setassoc, formula=self.formula,
                    mode=self.mode, pop=self.pop)


# ---------------------------------------------------------------- learning stats
def summarize(learn, gt=True):
    """Per-key learning counts and Good-Turing tail rates (per stream query)."""
    keys, counts = np.unique(learn, return_counts=True)
    L = len(learn)
    Nc = np.bincount(counts)
    adj = counts.astype(np.float64)
    for c in range(1, GT_MAX + 1):
        if gt and c < len(Nc) and Nc[c]:
            nxt = Nc[c + 1] if c + 1 < len(Nc) else 0
            adj[counts == c] = min(c, (c + 1) * nxt / Nc[c])
    return SimpleNamespace(keys=keys, counts=counts, rate=adj / L, L=L,
                           N1=(int(Nc[1]) if len(Nc) > 1 else 0) if gt else 0,
                           state_bytes=keys.nbytes + counts.nbytes)


def tree_setup(setup, scores, t):
    key = (id(setup), t)
    if key not in R._GSETUPS:
        R._GSETUPS[key] = R.gama_setup(setup, scores[t])
    gs = R._GSETUPS[key]
    if (setup.name, t) not in R._MODEL_ARRAYS:
        from end_to_end import model_arrays
        booster = lgb.Booster(model_file=str(C.CACHE / setup.name / 'model200.txt'))
        R._MODEL_ARRAYS[setup.name, t] = model_arrays(booster, t)
    return gs


def fixed_bytes(setup, scores, t):
    """Model + navigation + array headers, exactly as runtime.structure (no sketch)."""
    gs = tree_setup(setup, scores, t)
    arrays = R._MODEL_ARRAYS[setup.name, t]
    nr = len(gs.cuts) + 1
    metadata = gs.cuts.astype(np.float64).nbytes + nr * (1 + 8 + 8) + (nr + 1) * 8
    overhead = 12 * R._sys.getsizeof(np.empty(0, np.uint8)) + R._sys.getsizeof(arrays)
    return sum(a.nbytes for a in arrays.values()) + metadata + overhead


def segment_arrays(gs):
    nr = len(gs.cuts) + 1
    n = np.bincount(np.searchsorted(gs.cuts, gs.mem_score, side='right'), minlength=nr).astype(np.float64)
    cnt = np.bincount(np.searchsorted(gs.cuts, gs.val_score, side='right'), minlength=nr)
    h = (cnt + .5) / (cnt.sum() + .5 * nr)
    return n, h


# ---------------------------------------------------------------- populations
class Population:
    """Per segment: (rate, multiplicity) groups plus unseen-key tail misses G.

    M and O are tabulated once on a log grid of T, so every later solve is a
    handful of (grid x segments) vector operations.
    """
    NT = 160

    def __init__(self, seg, lam, w, G, n, h, H):
        self.n, self.h, self.H, self.K = n, h, float(H), len(n)
        a = 1 - np.exp(-lam * H)               # P(key appears in the tail)
        rest = np.maximum(0., lam * H - a)
        self.T = np.concatenate([[0.], np.logspace(0, np.log10(1e3 * H), self.NT)])
        self.Mg = np.empty((len(self.T), self.K))
        self.Og = np.empty((len(self.T), self.K))
        for j, T in enumerate(self.T):
            x = np.exp(-lam * T)
            self.Mg[j] = np.bincount(seg, w * (a + rest * x), self.K) + G
            self.Og[j] = np.bincount(seg, w * (1 - np.exp(-lam * min(T, H))), self.K) + G / H * min(T, H)
        self.A = np.bincount(seg, w * a, self.K) + G    # distinct keys expected in the tail

    @classmethod
    def empirical(cls, lm, gs, H, new_mix=NEW_MIX):
        n, h = segment_arrays(gs)
        K = len(n)
        seg = np.searchsorted(gs.cuts, gs.q_score[lm.keys], side='right')
        urate, ridx = np.unique(lm.rate, return_inverse=True)
        w = np.bincount(seg * len(urate) + ridx, minlength=K * len(urate)).astype(np.float64)
        nz = np.flatnonzero(w)
        f1 = np.bincount(seg[lm.counts == 1], minlength=K)
        G = H * lm.N1 / lm.L * (new_mix * f1 / max(lm.N1, 1) + (1 - new_mix) * h)
        return cls(nz // len(urate), urate[nz % len(urate)], w[nz], G, n, h, H)

    @classmethod
    def zipf(cls, lm, gs, H, bins):
        """Ablation: per segment only (Q_i, D_i, top-256 mass) -> Zipf (W_i, s_i)."""
        n, h = segment_arrays(gs)
        K = len(n)
        seg = np.searchsorted(gs.cuts, gs.q_score[lm.keys], side='right')
        segs, lams, ws = [np.zeros(0, np.int64)], [np.zeros(0)], [np.zeros(0)]
        order = np.argsort(seg, kind='stable')
        bounds = np.searchsorted(seg[order], np.arange(K + 1))
        for i in range(K):
            c = lm.counts[order[bounds[i]:bounds[i + 1]]]
            if not len(c):
                continue
            Q, D = int(c.sum()), len(c)
            top = np.sort(c)[::-1][:256].sum() / Q
            W, s = fit_stream(Q, D, top)
            counts, prob = bins(W, s)
            segs.append(np.full(len(counts), i))
            lams.append(prob * Q / lm.L)
            ws.append(counts)
        return cls(np.concatenate(segs), np.concatenate(lams), np.concatenate(ws),
                   np.zeros(K), n, h, H)

    def at_capacity(self, e, caps):
        """Per-segment misses (rows) when a fully associative cache holds `caps` slots."""
        occ = self.Og @ e
        caps = np.atleast_1d(np.asarray(caps, np.float64))
        j = np.clip(np.searchsorted(occ, caps), 1, len(occ) - 1)
        lo, hi = occ[j - 1], occ[j]
        f = np.clip((caps - lo) / np.where(hi > lo, hi - lo, 1), 0, 1)[:, None]
        out = self.Mg[j - 1] * (1 - f) + self.Mg[j] * f
        out[caps >= occ[-1]] = self.Mg[-1]
        return out

    def misses(self, e, S, setassoc=True):
        """Per-segment misses for S slots in WAYS-way buckets.

        A bucket that receives X of the d keys it gets on average holds the share
        X/(d*B) of the population in WAYS slots, i.e. behaves like a fully
        associative cache of S*d/X slots for the whole population (X ~ Poisson(d)).
        """
        if S == 0:
            return self.Mg[0].copy()
        d = float(e @ self.A) / (S // WAYS)
        if not setassoc or d > 64:
            return self.at_capacity(e, S)[0]
        X = np.arange(1, int(np.ceil(d + 10 * np.sqrt(d) + 10)) + 1, dtype=np.float64)
        logp = X * np.log(max(d, 1e-300)) - d - np.cumsum(np.log(X))
        wt = np.exp(logp) * X
        wt /= wt.sum()
        return wt @ self.at_capacity(e, S * d / X)


def eps_closed(M, n, bits):
    """PLBF's continuous optimum: eps_i = min(1, mu*n_i/(ln2^2*M_i)) spending `bits`."""
    eps = np.where(n > 0, 1., 0.)
    act = (n > 0) & (M > 0)
    if bits <= 0 or not act.any():
        return eps
    nn, MM = n[act], M[act]

    def at(lmu):
        return np.minimum(1., np.exp(lmu) * nn / (LN2SQ * MM))

    lo, hi = -80., 80.
    for _ in range(60):
        mid = (lo + hi) / 2
        if (nn * -np.log(at(mid))).sum() / LN2SQ <= bits:
            hi = mid
        else:
            lo = mid
    eps[act] = at(hi)
    return eps


def weights_for(P, M, mode):
    return {'ra': M, 'norepeat': P.Mg[0], 'global': P.h}[mode]


def solve(P, S, bits, mode, refine=3, setassoc=True):
    """Consistent eps for a cache of S slots; returns (eps, predicted tail FP)."""
    if S == 0:
        e = eps_closed(weights_for(P, P.Mg[0], mode), P.n, bits)
        return e, float(e @ P.Mg[0])

    def fits(j):
        e = eps_closed(weights_for(P, P.Mg[j], mode), P.n, bits)
        return e, float(P.Og[j] @ e) <= S

    lo, hi = 0, len(P.T) - 1
    e, ok = fits(hi)
    if not ok:
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if fits(mid)[1]:
                lo = mid
            else:
                hi = mid
        e = fits(lo)[0]
    for _ in range(refine if setassoc else 0):
        e = eps_closed(weights_for(P, P.misses(e, S), mode), P.n, bits)
    return e, float(e @ P.misses(e, S, setassoc))


def eps_closed_cache(M, O, n, bits, b):
    """Design-sheet closed form with the cache inside the budget:
    eps_i = min(1, mu*n_i/(ln2^2*(M_i + mu*b*O_i))), mu bisected so that
    sum_i n_i*ln(1/eps_i)/ln2^2 + b*sum_i eps_i*O_i = bits."""
    eps = np.where(n > 0, 1., 0.)
    act = n > 0
    nn, MM, OO = n[act], M[act], O[act]

    def at(lmu):
        mu = np.exp(lmu)
        den = LN2SQ * (MM + mu * b * OO)
        return np.where(den > 0, np.minimum(1., mu * nn / np.where(den > 0, den, 1)), 1.)

    def memory(e):
        return (nn * -np.log(e)).sum() / LN2SQ + b * (e * OO).sum()

    lo, hi = -80., 80.
    for _ in range(60):
        mid = (lo + hi) / 2
        if memory(at(mid)) <= bits:
            hi = mid
        else:
            lo = mid
    eps[act] = at(hi)
    return eps


def slot_bits(slots):
    """Measured bits per slot of the physical layout closest to `slots` (allocated bytes incl. headers)."""
    best = None
    for alloc, S in layouts(1 << 40):
        if S and (best is None or abs(np.log(S / max(slots, 1))) < abs(np.log(best[1] / max(slots, 1)))):
            best = (alloc, S)
        if S > 4 * max(slots, 1):
            break
    return best[0] * 8 / best[1]


def solve_table(P, bits):
    """Design-sheet solver: 1-D search over T; returns (eps, predicted FP, slots needed)."""
    best = None
    b = slot_bits(1024)
    for _ in range(2):                          # b depends on the cache size it implies
        best = None
        for j in range(len(P.T)):
            e = eps_closed_cache(P.Mg[j], P.Og[j], P.n, bits, b)
            pred = float(e @ P.Mg[j])
            if best is None or pred < best[1]:
                best = (e, pred, float(P.Og[j] @ e), j)
        b = slot_bits(best[2])
    return best


# ---------------------------------------------------------------- physical cache sizes
def layouts(max_bytes):
    """Every distinct CLOCK layout (exact allocated bytes, slots) that fits."""
    out = [(0, 0)]
    hb = int(np.log2(WAYS))
    for q in range(1, PREFIX):
        r = PREFIX - q
        sb = r + 8
        buckets = 1 << q
        slots = WAYS * buckets
        words = F.HEAD + (slots * sb + buckets * hb + 63) // 64
        alloc = words * 8 + F.ARRAY_HEADER
        if alloc > max_bytes:
            break
        assert F.layout(alloc, PREFIX, 'clock', WAYS)['slots'] == slots
        out.append((alloc, slots))
    return out


# ---------------------------------------------------------------- build
def build_structure(setup, scores, t, budget_bytes, cache_bytes, weights):
    """runtime.structure with PLBF weights `weights` instead of validation h."""
    gs = tree_setup(setup, scores, t)
    arrays = R._MODEL_ARRAYS[setup.name, t]
    cuts = gs.cuts.astype(np.float64)
    nr = len(cuts) + 1
    model_bytes = sum(a.nbytes for a in arrays.values())
    metadata_bytes = cuts.nbytes + nr * (1 + 8 + 8) + (nr + 1) * 8
    array_overhead_bytes = 12 * R._sys.getsizeof(np.empty(0, np.uint8)) + R._sys.getsizeof(arrays)
    fixed = model_bytes + metadata_bytes + array_overhead_bytes + cache_bytes
    if fixed >= budget_bytes:
        return None
    regions = np.searchsorted(cuts, gs.mem_score, side='right').astype(np.int32)
    n, h = segment_arrays(gs)
    kind, param, _, _ = C.allocate(n, np.asarray(weights, np.float64), (budget_bytes - fixed) * 8, 'bf')
    kind = kind.astype(np.uint8)
    m = np.where(kind == C.BF, np.maximum(1, np.floor(param * n)), 0).astype(np.int64)
    k = np.where(kind == C.BF, np.maximum(1, np.rint(param * np.log(2))), 0).astype(np.int64)
    off = np.concatenate([[0], np.cumsum(m)]).astype(np.int64)
    bits = np.zeros((int(off[-1]) + 7) // 8, np.uint8)
    R.packed_build(setup.h1m, regions, off, m, k, bits)
    assert R.packed_query(setup.h1m, regions, kind, off, m, k, bits).all(), 'Packed Bloom false negative'
    rq = np.searchsorted(cuts, gs.q_score, side='right').astype(np.int32)
    fp = R.packed_query(setup.h1q, rq, kind, off, m, k, bits)
    used = fixed + bits.nbytes
    assert used <= budget_bytes
    seg_fpr = np.where(kind == C.PASS, 1., np.where(kind == C.BF, C.bf_fpr(np.maximum(param, 1e-9)), 0.))
    est = float((h * seg_fpr)[n > 0].sum())
    return SimpleNamespace(name=f't{t}', trees=t, cuts=cuts, kind=kind, m=m, k=k, bf_off=off, bits=bits,
                           fp_static=fp, est_fpr=est, seg_fpr=seg_fpr, q_region=rq,
                           model_arrays=arrays, model_bytes=model_bytes, metadata_bytes=metadata_bytes,
                           array_overhead_bytes=array_overhead_bytes, filter_bytes=bits.nbytes,
                           cache_bytes=cache_bytes, sketch_bytes=0, used_bytes=used,
                           budget_bytes=budget_bytes, member_false_negatives=0)


# ---------------------------------------------------------------- selection
def select(setup, scores, lm, kib, H, mode='ra', pop='emp', bins=None, cfg=None):
    """Enumerate tree counts x cache layouts; deploy the best predicted configuration."""
    cfg = cfg or Config(new_mix=NEW_MIX, mode=mode, pop=pop)
    mode, pop = cfg.mode, cfg.pop
    if cfg.formula == 'table':
        return select_table(setup, scores, lm, kib, H, cfg)
    t0 = time.perf_counter()
    budget = kib * 1024
    best, grid, pops = None, [], {}
    for t in R.GAMA_TREES:
        fixed = fixed_bytes(setup, scores, t)
        if fixed >= budget:
            continue
        gs = tree_setup(setup, scores, t)
        P = Population.empirical(lm, gs, H, cfg.new_mix) if pop == 'emp' else Population.zipf(lm, gs, H, bins)
        pops[t] = P
        for alloc, S in layouts(budget - fixed - 1):
            e, pred = solve(P, S, (budget - fixed - alloc) * 8, mode, setassoc=cfg.setassoc)
            grid.append(dict(trees=t, cache_bytes=alloc, slots=S, predicted_fp=pred,
                             passed_segments=int(((e >= 1) & (P.n > 0)).sum())))
            key = (pred, t, alloc)
            if best is None or key < best[0]:
                best = (key, t, alloc, S, e)
    _, t, alloc, S, e = best
    P = pops[t]
    st = build_structure(setup, scores, t, budget, alloc, weights_for(P, P.misses(e, S, cfg.setassoc), mode))
    seg_pred = st.seg_fpr * P.misses(st.seg_fpr, S, cfg.setassoc)     # re-predicted with the deployed FPRs
    seg_pred_sa = st.seg_fpr * P.misses(st.seg_fpr, S, True)          # same, with the set-associative model
    c = dict(trees=t, frac=alloc / budget, requested_cache_bytes=alloc, cache_bytes=alloc,
             policy='clock', prefix_bits=PREFIX, ways=WAYS, admit=1, structure=st)
    info = dict(mode=mode, population=pop, trees=t, cache_bytes=alloc, slots=S,
                predicted_fp=float(seg_pred.sum()), seg_predicted=seg_pred.tolist(),
                predicted_fp_setassoc=float(seg_pred_sa.sum()),
                predicted_fp_fullassoc=float((st.seg_fpr * P.misses(st.seg_fpr, S, False)).sum()),
                config=cfg.as_dict(),
                seg_kind=st.kind.tolist(), seg_members=P.n.tolist(),
                passed_segments=int(((st.kind == C.PASS) & (P.n > 0)).sum()),
                selection_seconds=time.perf_counter() - t0, grid=grid)
    return c, info


def select_table(setup, scores, lm, kib, H, cfg):
    """Design-sheet formula version (see module docstring)."""
    t0 = time.perf_counter()
    budget = kib * 1024
    best, grid = None, []
    for t in R.GAMA_TREES:
        fixed = fixed_bytes(setup, scores, t)
        if fixed >= budget:
            continue
        P = Population.empirical(lm, tree_setup(setup, scores, t), H, cfg.new_mix)
        e, pred, need, j = solve_table(P, (budget - fixed) * 8)
        grid.append(dict(trees=t, predicted_fp=pred, slots_needed=need, T=float(P.T[j])))
        if best is None or (pred, t) < best[0]:
            best = ((pred, t), t, P, j, need, fixed)
    _, t, P, j, need, fixed = best
    fits = [(a, S) for a, S in layouts(budget - fixed - 1) if S <= max(need, 0)]
    alloc, S = fits[-1]
    st = build_structure(setup, scores, t, budget, alloc, P.Mg[j])
    seg_pred = st.seg_fpr * P.misses(st.seg_fpr, S, False)
    c = dict(trees=t, frac=alloc / budget, requested_cache_bytes=alloc, cache_bytes=alloc,
             policy='clock', prefix_bits=PREFIX, ways=WAYS, admit=1, structure=st)
    info = dict(mode='ra', population='emp', trees=t, cache_bytes=alloc, slots=S, slots_solved=need,
                T=float(P.T[j]), predicted_fp=float(seg_pred.sum()), seg_predicted=seg_pred.tolist(),
                predicted_fp_setassoc=float((st.seg_fpr * P.misses(st.seg_fpr, S, True)).sum()),
                predicted_fp_fullassoc=float(seg_pred.sum()), config=cfg.as_dict(),
                seg_kind=st.kind.tolist(), seg_members=P.n.tolist(),
                passed_segments=int(((st.kind == C.PASS) & (P.n > 0)).sum()),
                selection_seconds=time.perf_counter() - t0, grid=grid)
    return c, info


def guarded(setup, scores, safe, learn, kib, H, gama, full, bins=None, cfg=None):
    """RA-PLBF+G: keep `full` (RA-PLBF on all learning) only if a fit on the first
    3/4 is not worse than Gama when both are replayed on the last 1/4."""
    t0 = time.perf_counter()
    cut = int(len(learn) * GUARD_SPLIT)
    fit, check = learn[:cut], learn[cut:]
    cfg = cfg or Config(new_mix=NEW_MIX)
    c, _ = select(setup, scores, summarize(fit, cfg.gt), kib, len(check), bins=bins, cfg=cfg)
    freq = np.bincount(check, minlength=len(setup.h1q))
    ra_fp = E.evaluate(c, check, setup, safe, freq)['fp']
    gama_fp = E.evaluate(gama, check, setup, safe, freq)['fp']
    keep = ra_fp <= gama_fp
    return (full if keep else gama), dict(guard_ra_fp=ra_fp, guard_gama_fp=gama_fp, kept_ra=bool(keep),
                                         guard_seconds=time.perf_counter() - t0)


# ---------------------------------------------------------------- per-segment measurement (C3)
@njit(cache=True)
def _replay_misses(stream, hashes, safe, fp, data, q, r, sb, ways, code, hb, miss):
    hits = 0
    for i in range(len(stream)):
        x = np.int64(stream[i])
        if F.lookup(data, hashes[x], q, r, sb, ways, code):
            hits += 1
        elif fp[x]:
            miss[x] += 1
            F.insert(data, hashes[x], safe[x], q, r, sb, ways, code, hb)
    return hits


def measure_segments(c, stream, setup, safe):
    """Exact per-key misses with the same cache code; returns per-segment FP and hits."""
    st = c['structure']
    spec = F.layout(c['cache_bytes'], c['prefix_bits'], c['policy'], c['ways'])
    data = F.allocate(spec)
    miss = np.zeros(len(setup.h1q), np.int64)
    hits = _replay_misses(np.asarray(stream, np.int64), setup.h1q, safe, st.fp_static, data, spec['qbits'],
                          spec['rbits'], spec['slot_bits'], c['ways'], spec['policy_code'], spec['handbits'], miss)
    K = len(st.kind)
    seg_fp = np.bincount(st.q_region, miss, K)
    static = np.bincount(st.q_region[stream], st.fp_static[stream].astype(np.float64), K)
    return seg_fp, static, int(hits)

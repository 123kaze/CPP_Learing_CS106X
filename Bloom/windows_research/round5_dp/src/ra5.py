"""Round-5 RA-PLBF on the FastPLBF DP allocator (F-A).

Population, Che/Good-Turing model, set-associative correction and the closed-form search
are imported unchanged from round4_ra_plbf/src/ra4.py (frozen).  What changes:
  * segments are the DP allocator's N=1000 equal-width score segments, h = (validation+1)
    normalised exactly as FastPLBF's prList;
  * cache candidates are the shared (trees x cache fraction) grid with arbitrary-bucket layouts;
  * for each candidate the continuous search gives per-segment misses M_i(S); the deployed
    allocation is FastPLBF_M with weights M_i(S) (+ 1e-6 * total * h_i so no segment has zero
    mass); the candidate's prediction uses the DP's own region FPRs;
  * without repeats M_i(S) is proportional to h_i, so the DP input -- and the structure -- is
    exactly Gama's (dp_weights snaps a proportional-up-to-rounding input to Gama's own array).
Variants: config flags of ra4.Config plus 'global' (RA-global: cache size chosen by the RA
prediction, Bloom allocation by the plain h) and formula 'table'.
"""
import sys
import time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'round4_ra_plbf' / 'src'))
import ra4  # noqa: E402  (frozen round-4 model code)
import engine5 as E5  # noqa: E402
import dp_alloc as D  # noqa: E402
import cache5 as K  # noqa: E402

Config = ra4.Config
FLOOR = 1e-6


def population(lm, td, H, cfg):
    """ra4.Population over the DP segments of one tree."""
    K_ = D.N_SEG
    seg = td.seg_q[lm.keys]
    urate, ridx = np.unique(lm.rate, return_inverse=True)
    w = np.bincount(seg * len(urate) + ridx, minlength=K_ * len(urate)).astype(np.float64)
    nz = np.flatnonzero(w)
    f1 = np.bincount(seg[lm.counts == 1], minlength=K_)
    G = H * lm.N1 / lm.L * (cfg.new_mix * f1 / max(lm.N1, 1) + (1 - cfg.new_mix) * td.h)
    return ra4.Population(nz // len(urate), urate[nz % len(urate)], w[nz], G, td.g.astype(np.float64), td.h, H)


def dp_weights(P, M, td):
    """DP input for misses M; numerically snapped to Gama's exact input (validation+1) when M is
    proportional to h up to rounding (relative 1e-12), so the no-repeat case is bit-identical."""
    M = np.asarray(M, np.float64)
    w = M + FLOOR * max(M.sum(), 1e-300) * P.h
    if w.sum() > 0 and np.allclose(w / w.sum(), td.h, rtol=1e-12, atol=0):
        return td.v + 1.0
    return w


def dp_fpr(td, w, bits):
    """Per-segment FPR of the FastPLBF_M allocation with weights w (continuous region FPRs)."""
    b, f, _ = D.allocate(td.g, w, float(bits))
    reg = D.region_of_segment(b)
    n = np.bincount(reg, weights=td.g, minlength=len(f))
    return np.where(n[reg] > 0, f[reg], 0.)


def candidate_table(setup, scores, lm, kib, H, cfg, fracs=E5.FRACS, trees=E5.TREES, extra_predictors=None):
    """Predicted tail FP of every (trees, fraction) candidate under `cfg`.

    Returns list of dicts with trees, frac, cache_bytes, slots, weights (for deployment),
    pred (cfg's own prediction) and preds_other {name: prediction of the same structure by
    another predictor population} for E3.
    """
    budget = kib * 1024
    out = []
    for t in trees:
        td = E5.tree(setup, scores, t)
        if td.fixed >= budget:
            continue
        P = population(lm, td, H, cfg)
        others = {k: population(o_lm, td, H, o_cfg) for k, (o_lm, o_cfg) in (extra_predictors or {}).items()}
        for frac in fracs:
            cache_bytes, S = E5.cache_alloc(budget, frac)
            bits = (budget - td.fixed - cache_bytes) * 8
            if bits <= 0:
                continue
            if cfg.mode == 'global':
                w = td.v + 1.0
            else:
                e, _ = ra4.solve(P, S, bits, 'norepeat' if cfg.mode == 'norepeat' else 'ra', setassoc=cfg.setassoc)
                M = P.misses(e, S, cfg.setassoc) if cfg.mode != 'norepeat' else P.Mg[0]
                w = dp_weights(P, M, td)
            fpr = dp_fpr(td, w, bits)
            pred = float(fpr @ P.misses(fpr, S, cfg.setassoc))
            row = dict(trees=t, frac=frac, cache_bytes=cache_bytes, slots=S, weights=w, pred=pred,
                       pred_fullassoc=float(fpr @ P.misses(fpr, S, False)), seg_fpr_pred=fpr)
            row['preds_other'] = {k: float(fpr @ Po.misses(fpr, S, True)) for k, Po in others.items()}
            out.append(row)
    return out


def select(setup, scores, lm, kib, H, cfg, fracs=E5.FRACS, trees=E5.TREES, keep_table=False, extra_predictors=None):
    t0 = time.perf_counter()
    if cfg.formula == 'table':
        return select_table(setup, scores, lm, kib, H, cfg)
    table = candidate_table(setup, scores, lm, kib, H, cfg, fracs, trees, extra_predictors)
    best = min(table, key=lambda r: (r['pred'], r['trees'], r['frac']))
    sel_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    weights = None if cfg.mode == 'global' else best['weights']
    c = E5.build(setup, scores, best['trees'], kib, best['frac'], weights=weights,
                 cache_bytes=best['cache_bytes'], slots=best['slots'])
    info = dict(config=cfg.as_dict(), trees=best['trees'], frac=best['frac'], predicted_fp=best['pred'],
                select_seconds=sel_s, build_seconds=time.perf_counter() - t1, candidates=len(table))
    if keep_table:
        info['table'] = table
    return c, info


def select_table(setup, scores, lm, kib, H, cfg):
    """Design-sheet formula on DP segments: continuous closed form with the cache in the budget,
    1-D search over T, fully associative; deploy the solved cache size and DP weights M(T*)."""
    t0 = time.perf_counter()
    budget = kib * 1024
    best = None
    for t in E5.TREES:
        td = E5.tree(setup, scores, t)
        if td.fixed >= budget:
            continue
        P = population(lm, td, H, cfg)
        e, pred, need, j = ra4.solve_table(P, (budget - td.fixed) * 8)
        if best is None or (pred, t) < best[0]:
            best = ((pred, t), t, P, j, need, td)
    _, t, P, j, need, td = best
    B = int(need // E5.WAYS)
    cache_bytes = K._bytes(B, E5.PREFIX, E5.WAYS)[0] if B >= 1 else 0
    if cache_bytes >= budget - td.fixed:
        cache_bytes = 0
    S = K.layout(cache_bytes)['slots'] if cache_bytes else 0
    sel_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    c = E5.build(setup, scores, t, kib, cache_bytes / budget, weights=dp_weights(P, P.Mg[j], td), cache_bytes=cache_bytes, slots=S)
    info = dict(config=cfg.as_dict(), trees=t, frac=cache_bytes / budget, predicted_fp=float(pred),
                select_seconds=sel_s, build_seconds=time.perf_counter() - t1, candidates=len(E5.TREES) * len(P.T))
    return c, info

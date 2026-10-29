"""Speed-up of ra5.select (not part of the round-5 freeze; verified separately by verify_fast.py).

Rank every (trees, cache fraction) candidate by the continuous closed-form prediction that
ra4.solve already returns, then run the FastPLBF DP (and the DP-based prediction) only for the
best `topk`.  If, on every completed round-5 case, the chosen (trees, fraction) equals
ra5.select's, this is a pure speed-up; any difference makes it a new method (round 6).
"""
import time
import numpy as np
import ra5 as RA

E5, ra4 = RA.E5, RA.ra4


def select_fast(setup, scores, lm, kib, H, cfg, topk=10, fracs=E5.FRACS, trees=E5.TREES):
    t0 = time.perf_counter()
    budget = kib * 1024
    rough = []
    pops = {}
    for t in trees:
        td = E5.tree(setup, scores, t)
        if td.fixed >= budget:
            continue
        P = RA.population(lm, td, H, cfg)
        pops[t] = (P, td)
        for frac in fracs:
            cache_bytes, S = E5.cache_alloc(budget, frac)
            bits = (budget - td.fixed - cache_bytes) * 8
            if bits <= 0:
                continue
            e, pred_cont = ra4.solve(P, S, bits, 'ra', setassoc=cfg.setassoc)
            rough.append((pred_cont, t, frac, cache_bytes, S, bits, e))
    rough.sort(key=lambda r: (r[0], r[1], r[2]))
    best = None
    for pred_cont, t, frac, cache_bytes, S, bits, e in rough[:topk]:
        P, td = pops[t]
        w = RA.dp_weights(P, P.misses(e, S, cfg.setassoc), td)
        fpr = RA.dp_fpr(td, w, bits)
        pred = float(fpr @ P.misses(fpr, S, cfg.setassoc))
        key = (pred, t, frac)
        if best is None or key < best[0]:
            best = (key, t, frac, cache_bytes, S, w)
    _, t, frac, cache_bytes, S, w = best
    sel_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    c = E5.build(setup, scores, t, kib, frac, weights=w, cache_bytes=cache_bytes, slots=S)
    return c, dict(trees=t, frac=frac, predicted_fp=best[0][0], select_seconds=sel_s,
                   build_seconds=time.perf_counter() - t1, candidates=len(rough), dp_runs=min(topk, len(rough)))

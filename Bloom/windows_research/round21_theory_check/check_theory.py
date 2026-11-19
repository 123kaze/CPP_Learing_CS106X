"""Small independent algebra/boundary checks; no data loading, training or frozen imports.

Run with Bloom/.condaenv/bin/python -I /absolute/path/check_theory.py.
Only this directory's numerical_checks.json is written.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import brentq, minimize, minimize_scalar

HERE = Path(__file__).resolve().parent
WR = HERE.parent
SEED = 20261119


def kl(p, r):
    p, r = np.asarray(p, float), np.asarray(r, float)
    s = p > 0
    if np.any(r[s] == 0):
        return math.inf
    return float(p[s] @ np.log(p[s] / r[s]))


def interior(p, r, beta):
    return math.exp(-beta - kl(p, r)) * p / r


def capped(p, r, beta):
    """Exact convex optimum in x_i = log(1/epsilon_i), p @ x <= beta.

    p must be strictly positive; r may be zero. Zero-member regions are
    deliberately excluded here and treated separately in the report.
    """
    p, r = np.asarray(p, float), np.asarray(r, float)
    assert np.all(p > 0) and np.all(r >= 0) and beta >= 0
    active = r > 0
    epsilon = np.ones_like(p)
    if not active.any() or beta == 0:
        return epsilon
    z = np.log(r[active] / p[active])
    pp = p[active]
    log_c = brentq(
        lambda t: float(pp @ np.maximum(z - t, 0)) - beta,
        float(z.min() - beta / pp.sum() - 2),
        float(z.max() + 1),
        xtol=1e-13,
    )
    epsilon[active] = np.exp(-np.maximum(z - log_c, 0))
    return epsilon


def interior_mismatch(p, r, q):
    ratio = r / q
    return float(p @ ratio) * math.exp(-float(p @ np.log(ratio)))


def active_set_value(p, r, beta, epsilon):
    a = epsilon < 1 - 1e-10
    pa, ra = float(p[a].sum()), float(r[a].sum())
    if not a.any():
        return float(r.sum())
    da = kl(p[a] / pa, r[a] / ra)
    return float(r[~a].sum()) + ra * math.exp(-beta / pa - da)


def dm_loglike(alpha, counts, h):
    """DM log marginal without multinomial coefficient, stable at alpha=infinity."""
    counts, h = np.asarray(counts, int), np.asarray(h, float)
    assert np.all(h > 0) and np.isclose(h.sum(), 1)
    n = int(counts.sum())
    if n == 0:
        return 0.0
    if alpha == 0:
        nz = np.flatnonzero(counts)
        return float(np.log(h[nz[0]])) if len(nz) == 1 else -math.inf
    base = float(counts @ np.log(h))
    if math.isinf(alpha):
        return base
    numer = sum(float(np.log1p(np.arange(1, c) / (alpha * hi)).sum())
                for c, hi in zip(counts, h))
    denom = float(np.log1p(np.arange(1, n) / alpha).sum())
    return base + numer - denom


def dm_case(counts, h):
    counts, h = np.asarray(counts, int), np.asarray(h, float)
    n = int(counts.sum())
    base = dm_loglike(math.inf, counts, h)
    result = dict(counts=counts.tolist(), h=h.tolist(), N1=n, loglike_infinity=base)
    if n < 2:
        result.update(endpoint='unidentifiable', alpha=None)
        return result
    grid = np.linspace(-20, 20, 401)
    vals = np.array([dm_loglike(math.exp(t), counts, h) for t in grid])
    k = int(vals.argmax())
    fit = minimize_scalar(lambda t: -dm_loglike(math.exp(t), counts, h),
                          bounds=(grid[max(0, k-1)], grid[min(len(grid)-1, k+1)]),
                          method='bounded', options={'xatol': 1e-10})
    best_alpha, best_value = math.exp(fit.x), -float(fit.fun)
    lo = dm_loglike(0, counts, h)
    if lo >= max(base, best_value):
        endpoint, alpha, shrink = 'zero', 0.0, counts / n
    elif base >= best_value:
        endpoint, alpha, shrink = 'infinity', None, h
    else:
        endpoint, alpha = 'finite', best_alpha
        shrink = (counts + alpha * h) / (n + alpha)
    coefficient = float((counts * (counts - 1) / h).sum() - n * (n - 1)) / 2
    result.update(endpoint=endpoint, alpha=alpha, posterior_mean=shrink.tolist(),
                  loglike_best_finite=best_value, best_finite_alpha=best_alpha,
                  loglike_zero=lo if math.isfinite(lo) else None,
                  expansion_1_over_alpha_coefficient=coefficient)
    return result


def repaired_gt_total(key_counts):
    counts = np.asarray(key_counts, int)
    nc = np.bincount(counts)
    adjusted = counts.astype(float)
    for c in range(1, 6):
        if c < len(nc) and nc[c]:
            nxt = int(nc[c+1]) if c+1 < len(nc) else 0
            if c >= 2 and nxt == 0:
                continue
            adjusted[counts == c] = min(c, (c+1)*nxt/nc[c])
    n1 = int(nc[1]) if len(nc) > 1 else 0
    return float((adjusted.sum() + n1) / counts.sum())


def small_clock(stream, ways=4):
    """One bucket, exact identities, every key a static FP, no bypass, cold start."""
    slots, reference, hand, misses = [None]*ways, [0]*ways, 0, 0
    for key in stream:
        if key in slots:
            reference[slots.index(key)] = 1
            continue
        misses += 1
        if None in slots:
            choice = slots.index(None)
        else:
            for _ in range(ways*2):
                if reference[hand] == 0:
                    break
                reference[hand] = 0
                hand = (hand+1) % ways
            choice = hand
            hand = (choice+1) % ways
        slots[choice], reference[choice] = key, 1
    return misses


def archive_schema():
    rels = ['round6_bucket/results/e3_seeds/cod_256.json',
            'round19_gt_fix/results/rerun_cod_index.json',
            'round20_zero_guard/results/main/caida_tcp_flow_fp64.json']
    out = []
    for rel in rels:
        path = WR / rel
        if not path.exists():
            out.append(dict(path=str(path), available=False))
            continue
        raw = path.read_bytes()
        obj = json.loads(raw)
        if isinstance(obj, list):
            fields = list(obj[0])
            detail = 'rank_rows: trees, frac, aggregate_RA4, aggregate_bucket, measured_FP'
        else:
            fields = list(obj['cases'][0])
            detail = ('candidate_changes: aggregate predictions and measured FP'
                      if 'round19_' in rel else 'gate and method aggregates; no segment vectors')
        out.append(dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(),
                        sample_fields=fields, detail=detail))
    return dict(inspected=out, formula_scatter_done=False,
                reason='These archives do not save candidate region n_i, M_i(T), q_i, T or active sets. '
                       'No formula inputs are inferred from aggregate FP.')


def main():
    rng = np.random.default_rng(SEED)
    max_a_error = max_b_error = max_budget_error = max_slsqp_error = 0.0
    for _ in range(80):
        k = int(rng.integers(2, 9))
        p, r, q = [rng.dirichlet(np.full(k, 2.5)) for _ in range(3)]
        thresholds = [float(np.log(p / w).max()) - kl(p, w) for w in (r, q)]
        beta = max(thresholds) + float(rng.uniform(.2, 1))
        er, eq = interior(p, r, beta), interior(p, q, beta)
        assert er.max() < 1 and eq.max() < 1
        expected = math.exp(-beta - kl(p, r))
        a_error = abs(float(r @ capped(p, r, beta)) / expected - 1)
        b_error = abs(float(r @ eq) / float(r @ er) / interior_mismatch(p, r, q) - 1)
        max_a_error, max_b_error = max(max_a_error, a_error), max(max_b_error, b_error)
        max_budget_error = max(max_budget_error, abs(float(p @ -np.log(er)) - beta))
        assert a_error < 1e-10 and b_error < 1e-10
    for _ in range(30):
        k = int(rng.integers(2, 7))
        p, r = [rng.dirichlet(np.full(k, 2.5)) for _ in range(2)]
        beta = float(rng.uniform(.02, 2))
        e = capped(p, r, beta)
        fit = minimize(lambda x: float(r @ np.exp(-x)), np.full(k, beta),
                       jac=lambda x: -r*np.exp(-x), bounds=[(0, None)]*k,
                       constraints=[dict(type='eq', fun=lambda x: float(p @ x)-beta,
                                         jac=lambda x: p)], method='SLSQP',
                       options={'ftol': 1e-13, 'maxiter': 500})
        assert fit.success, fit.message
        err = abs(float(fit.fun) - float(r @ e))
        max_slsqp_error = max(max_slsqp_error, err)
        assert err < 1e-9
        assert abs(active_set_value(p, r, beta, e) - float(r @ e)) < 1e-10
    result = dict(seed=SEED, numpy=np.__version__, scipy=scipy.__version__,
                  random_interior_cases=80, independent_slsqp_cases=30,
                  max_A_relative_error=max_a_error, max_B_relative_error=max_b_error,
                  max_dimensionless_budget_error=max_budget_error,
                  max_slsqp_objective_error=max_slsqp_error)
    p, r, beta, delta = np.array([.5,.5]), np.array([.99,.01]), .1, .2
    e, erel = capped(p, r, beta), interior(p, r, beta)
    relax, real, bf = math.exp(-beta-kl(p,r)), float(r@e), math.exp(-beta-delta)
    assert relax < bf < real
    result['A_clipping_gate_reversal'] = dict(p=p.tolist(), r=r.tolist(), beta_learned=beta,
        delta_overhead=delta, KL=kl(p,r), relaxed_FP=relax, capped_FP=real, plain_BF_FP=bf,
        relaxed_ratio=relax/bf, capped_ratio=real/bf, relaxed_epsilon=erel.tolist(),
        capped_epsilon=e.tolist(), clamp_without_resolve_budget=float(p @ -np.log(np.minimum(erel,1))))
    q = np.array([.5,.5])
    lo = float(r@capped(p,q,beta))/float(r@capped(p,r,beta))
    result['B_clipping_below_formula'] = dict(p=p.tolist(),r=r.tolist(),q=q.tolist(),beta=beta,
        capped_ratio=lo,interior_formula=interior_mismatch(p,r,q))
    p,r,q = np.array([.5,.1,.4]),np.array([.15,.45,.4]),np.array([.2,.15,.65])
    hi = float(r@capped(p,q,.6))/float(r@capped(p,r,.6))
    assert hi > interior_mismatch(p,r,q)
    result['B_clipping_above_formula'] = dict(p=p.tolist(),r=r.tolist(),q=q.tolist(),beta=.6,
        capped_ratio=hi,interior_formula=interior_mismatch(p,r,q))
    p,r,q = np.array([.5,.5]),np.array([.99,.01]),np.array([.01,.99])
    beta=3.
    actual_ratio=float(r@interior(p,q,beta))/math.exp(-beta)
    assert actual_ratio>1 and interior(p,q,beta).max()<1 and interior(p,r,beta).max()<1
    result['true_KL_alone_not_plugin_guarantee'] = dict(p=p.tolist(),r=r.tolist(),q=q.tolist(),
        beta=beta,KL_true=kl(p,r),oracle_ratio=math.exp(-kl(p,r)),plugin_ratio=actual_ratio)
    p,r = np.array([.5,.5]),np.array([1.,0.])
    result['r_zero_boundary'] = dict(p=p.tolist(),r=r.tolist(),beta=.1,KL='infinity',
        naive_formula_FP=0.,capped_FP=float(r@capped(p,r,.1)))
    assert result['r_zero_boundary']['capped_FP'] > 0
    result['partition_coarsening'] = dict(fine_p=[.25]*4, fine_r=[.49,.01,.49,.01],
        fine_KL=kl([.25]*4,[.49,.01,.49,.01]),two_region_KL=kl([.5,.5],[.5,.5]))
    dm = [dm_case(s,[.5,.5]) for s in ([5,5],[8,2],[10,0],[1,0],[0,0])]
    assert [x['endpoint'] for x in dm] == ['infinity','finite','zero','unidentifiable','unidentifiable']
    result['Dirichlet_EB'] = dm
    log_alphas=np.linspace(-10,20,200)
    vals=[dm_loglike(math.exp(a),[5,5],[.5,.5]) for a in log_alphas]
    assert np.diff(vals).min()>-1e-12
    result['true_h_half_N10_probability_infinity_not_max_by_expansion'] = sum(
        math.comb(10,k) for k in range(11) if k<=3 or k>=7) / 2**10
    over, under = repaired_gt_total([1,2]), repaired_gt_total([2]*10+[3])
    assert over>1 and under<1
    result['GT19_total_rate_examples'] = [dict(key_counts=[1,2],total_seen_plus_unseen=over),
        dict(key_counts=[2]*10+[3],total_seen_plus_unseen=under)]
    grouped=[k for k in range(5) for _ in range(3)]
    alternating=list(range(5))*3
    cg,ca = small_clock(grouped),small_clock(alternating)
    assert cg==5 and ca==15
    result['CLOCK_same_key_counts_different_order'] = dict(ways=4,buckets=1,
        grouped_stream=grouped,alternating_stream=alternating,grouped_FP=cg,alternating_FP=ca)
    result['archival_feasibility'] = archive_schema()
    result['all_assertions_passed'] = True
    dest=HERE/'numerical_checks.json'
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('archival_feasibility',)},
                     ensure_ascii=False,indent=2,allow_nan=False))
    print('OUTPUT',dest)


if __name__=='__main__':
    main()

"""Pure small-array diagnostics; no frozen modules, caches, datasets or plotting."""
import math

import numpy as np
from scipy.optimize import brentq, minimize_scalar
from scipy.special import gammaln

A = math.log(2) ** 2


def kl(p, r):
    p, r = np.asarray(p, float), np.asarray(r, float)
    active = p > 0
    if np.any(r[active] <= 0):
        return math.inf
    return float(p[active] @ np.log(p[active] / r[active]))


def capped(n, mass, bits):
    """Exact continuous allocation with EMPTY and zero-mass PASS handled explicitly."""
    n, mass = np.asarray(n, float), np.asarray(mass, float)
    if bits < 0 or np.any(n < 0) or np.any(mass < 0) or n.sum() <= 0:
        raise ValueError('Invalid nonnegative allocation inputs')
    eps = np.where(n > 0, 1., 0.)
    active = (n > 0) & (mass > 0)
    if bits == 0 or not active.any():
        return eps
    p = n / n.sum()
    beta = bits * A / n.sum()
    z = np.log(mass[active] / p[active])
    pp = p[active]
    c = brentq(lambda t: float(pp @ np.maximum(z-t, 0)) - beta,
               float(z.min() - beta / pp.sum() - 2), float(z.max() + 1), xtol=1e-13)
    eps[active] = np.exp(-np.maximum(z-c, 0))
    return eps


def theory_layers(n, mass, q, bits, plain_bits=None):
    n, mass, q = [np.asarray(x, float) for x in (n, mass, q)]
    p, W = n / n.sum(), float(mass.sum())
    eps = capped(n, mass, bits)
    base = dict(n=n.tolist(), p=p.tolist(), M=mass.tolist(), W=W,
                bits=float(bits), beta=float(A*bits/n.sum()),
                capped_epsilon=eps.tolist(), capped_FP=float(mass @ eps),
                active_set=np.flatnonzero((n > 0) & (eps < 1-1e-12)).tolist(),
                T=0., interpretation='fixed external T=0, continuous BF conditional model')
    if W == 0:
        base.update(r=None, KL=None, relaxed_FP=None, interior_legal=False, B=None,
                    degenerate_reason='zero total miss mass')
        return base
    r = mass / W
    d = kl(p, r)
    base.update(r=r.tolist(), KL=d if math.isfinite(d) else None,
                KL_infinite=not math.isfinite(d))
    rel_e = np.zeros(len(p))
    if math.isfinite(d):
        c = math.exp(-base['beta'] - d)
        active = p > 0
        rel_e[active] = c*p[active]/r[active]
        base.update(relaxed_FP=W*c, relaxed_epsilon=rel_e.tolist(),
                    interior_legal=bool(rel_e.max(initial=0) <= 1+1e-12))
    else:
        base.update(relaxed_FP=None, relaxed_epsilon=None, interior_legal=False)
    eq = capped(n, q, bits)
    denom = float(mass @ eps)
    loss = float(mass @ eq)/denom if denom > 0 else None
    B = dict(q=q.tolist(), capped_q_epsilon=eq.tolist(), capped_loss_ratio=loss,
             arithmetic_geometric_factor=None, interior_equality_applicable=False,
             scope='same partition, raw p, identical bit budget and external T=0 only')
    s = p > 0
    if np.all(q[s] > 0) and np.all(r[s] > 0):
        dq = kl(p, q)
        eq_rel = np.zeros_like(p)
        eq_rel[s] = math.exp(-base['beta']-dq)*p[s]/q[s]
        u = r[s]/q[s]
        B['arithmetic_geometric_factor'] = float(p[s] @ u)*math.exp(-float(p[s] @ np.log(u)))
        B['interior_equality_applicable'] = bool(base['interior_legal'] and eq_rel.max(initial=0) <= 1+1e-12)
        if B['interior_equality_applicable'] and denom > 1e-250:
            assert math.isclose(loss, B['arithmetic_geometric_factor'], rel_tol=1e-9, abs_tol=1e-10)
    base['B'] = B
    if plain_bits is not None:
        plain = W*math.exp(-A*plain_bits/n.sum())
        base.update(plain_bits=float(plain_bits), same_W_plain_proxy=plain,
                    extra_cost_delta=float(A*(plain_bits-bits)/n.sum()),
                    raw_KL_says_win=(d > A*(plain_bits-bits)/n.sum()) if math.isfinite(d) else None,
                    capped_same_W_says_win=bool(base['capped_FP'] < plain),
                    same_W_capped_ratio=base['capped_FP']/plain if plain > 0 else None)
    return base


def integer_fpr(n, m, k):
    n, m, k = [np.asarray(v, float) for v in (n, m, k)]
    out = np.where(n > 0, 1., 0.)
    active = (n > 0) & (m > 0)
    out[active] = (-np.expm1(-k[active]*n[active]/m[active]))**k[active]
    return out


def power_sums(n):
    n = np.asarray(n, float)
    return (n*(n-1)/2, n*(n-1)*(2*n-1)/6, n*n*(n-1)**2/4,
            (n-1)*n*(2*n-1)*(3*n*n-3*n-1)/30,
            (n-1)**2*n*n*(2*n*n-2*n-1)/12)


def dm_relative(alpha, s, h):
    """Log marginal minus its alpha=infinity limit; no multinomial coefficient."""
    s, h = np.asarray(s, float), np.asarray(h, float)
    N = float(s.sum())
    if math.isinf(alpha) or N < 2:
        return 0.
    if alpha == 0:
        nz = np.flatnonzero(s)
        return float(math.log(h[nz[0]]) - s @ np.log(h)) if len(nz) == 1 else -math.inf
    # Stable high-alpha expansion through fifth order; ratio <=.001 keeps
    # remainder <= O(N*1e-18), instead of subtracting huge log-gamma terms.
    if max(N/alpha, float(np.max(s/(alpha*h), initial=0))) <= .001:
        top, bottom = power_sums(s), power_sums(N)
        return float(sum((-1)**(j+1)/j * ((top[j-1]/(alpha*h)**j).sum()-bottom[j-1]/alpha**j)
                         for j in range(1, 6)))
    return float(gammaln(alpha)-gammaln(alpha+N)
                 + (gammaln(alpha*h+s)-gammaln(alpha*h)).sum()-s @ np.log(h))


def fit_eb(s, h, settings):
    s, h = np.asarray(s, int), np.asarray(h, float)
    if np.any(s < 0) or np.any(h <= 0) or not np.isclose(h.sum(), 1):
        raise ValueError('DM requires nonnegative counts and positive normalized h')
    N = int(s.sum())
    meta = dict(N1=N, model='DM working model', all_singleton_fallback=False)
    if N <= 1:
        return h.copy(), dict(meta, alpha=None, endpoint='unidentified-use-h', loglike_gain_over_infinity=0.)
    if np.count_nonzero(s) == 1:
        return s/N, dict(meta, alpha=0., endpoint='zero-limit', loglike_gain_over_infinity=dm_relative(0,s,h))
    low, high, size = settings['log_alpha_grid']
    grid = np.linspace(low, high, int(size))
    values = np.array([dm_relative(math.exp(x),s,h) for x in grid])
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite DM numerical objective')
    i = int(values.argmax())
    fit = minimize_scalar(lambda x: -dm_relative(math.exp(x),s,h),
                          bounds=(grid[max(0,i-1)],grid[min(len(grid)-1,i+1)]), method='bounded')
    options = [(float(values[i]),math.exp(grid[i])),(-float(fit.fun),math.exp(fit.x))]
    gain, alpha = max(options)
    if gain <= settings['numerical_likelihood_tolerance']:
        return h.copy(), dict(meta, alpha=None, endpoint='infinity-or-numerical-tie',
                             loglike_gain_over_infinity=0., best_finite_gain=gain,
                             best_finite_alpha=alpha)
    return (s+alpha*h)/(N+alpha), dict(meta, alpha=alpha,
        endpoint='finite-search-boundary' if i in (0,len(grid)-1) else 'finite-grid-refined',
        loglike_gain_over_infinity=gain, optimizer_success=bool(fit.success))

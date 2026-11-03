"""Offline check of the finite-window correction to the per-key miss formula (paper Eq. 7).

Frozen RA6 (round6_bucket/src/ra6.py, bucket_che) predicts the tail misses of a key with
Poisson rate lam, Che time T and evaluation window H (cold cache at the window start) as
    m(T) = a + (lam*H - a) * exp(-lam*T),   a = 1 - exp(-lam*H).
That charges every repeat with P(gap > T) = exp(-lam*T), although inside a window of length H
a repeat at time t can only miss if its previous request was also inside the window.  The exact
expectation under the same Poisson + Che assumptions is
    m(T) = a + exp(-lam*T) * [lam*(H-T) - (1 - exp(-lam*(H-T)))]   for T < H,   m(T) = a for T >= H.

Nothing is re-simulated and the method is not changed: for exactly the candidates of E3
(synthetic seeds 1-4: RA4's top 10; MAWI 2024 holdout: every candidate), the structures are
rebuilt and re-predicted from the actual bucket load with both formulas.  The original formula
must reproduce the stored RA6 prediction (assert), and the measured tail FPs are taken from E3.

usage: eq7_offline.py seeds <dataset> <kib>   -> results/seeds_<ds>_<kib>.json
       holdout6.py run eq7_offline.py holdout -> results/holdout_mawi2024_flow.json
rows: [trees, frac, RA4 pred, RA6 pred (orig), RA6 pred (corrected), measured]
"""
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R6 = HERE.parents[1] / 'round6_bucket'
sys.path.insert(0, str(R6 / 'src'))
import ra6  # noqa: E402  (frozen round 6)

E5, RA = ra6.E5, ra6.RA


def miss_orig(lam, T, H):
    a = -np.expm1(-lam * H)
    return a + np.maximum(0, lam * H - a) * np.exp(-lam * T)


def miss_corr(lam, T, H):
    a = -np.expm1(-lam * H)
    x = lam * np.maximum(H - T, 0.)
    return a + np.exp(-lam * T) * np.maximum(0., x + np.expm1(-x))


def bucket_che_T(lam, b, B, H, g_new, iters=60):
    """Per-bucket Che time, line for line as ra6.bucket_che (which returns only the sum)."""
    lo = np.zeros(B)
    hi = np.full(B, np.log(1e3 * H))
    cnt = np.bincount(b, minlength=B)
    for _ in range(iters):
        mid = (lo + hi) / 2
        T = np.minimum(np.exp(mid), H)
        occ = np.bincount(b, 1 - np.exp(-lam * T[b]), minlength=B) + g_new * T
        over = occ > ra6.WAYS
        hi = np.where(over, mid, hi)
        lo = np.where(over, lo, mid)
    T = np.exp(lo)
    return np.where((cnt <= ra6.WAYS) & (g_new * H <= ra6.WAYS - cnt), 1e3 * H, T)


def predictions(setup, lm, td, c, H, seg_fpr):
    """(original, corrected) bucket-load prediction, as ra6.bucket_prediction."""
    st = c['structure']
    fpk = st.fp_static[lm.keys]
    lam = lm.rate[fpk]
    G = H * lm.N1 / lm.L * td.h
    new_miss = float((seg_fpr * G).sum())
    if c['cache_bytes'] == 0:
        v = float((lam * H).sum()) + new_miss
        return v, v
    B = c['slots'] // ra6.WAYS
    b = ra6.buckets_of(setup.h1q[lm.keys[fpk]], B)
    T = bucket_che_T(lam, b, B, H, new_miss / H / B)[b]
    return float(miss_orig(lam, T, H).sum()) + new_miss, float(miss_corr(lam, T, H).sum()) + new_miss


def close(x, y):
    return abs(x - y) <= 1e-9 * max(1., abs(y))


def rescore(setup, scores, lm, kib, H, keys):
    """keys: [(trees, frac, stored RA4 pred, stored RA6 pred, measured)] -> rows."""
    table = {(r['trees'], r['frac']): r for r in RA.candidate_table(setup, scores, lm, kib, H, RA.Config(new_mix=0.))}
    rows = []
    for t, f, p4, p6, meas in keys:
        row = table[t, f]
        assert close(row['pred'], p4), (t, f, row['pred'], p4)
        c = E5.build(setup, scores, t, kib, f, weights=row['weights'],
                     cache_bytes=row['cache_bytes'], slots=row['slots'])
        td = E5.tree(setup, scores, t)
        po, pc = predictions(setup, lm, td, c, H, row['seg_fpr_pred'])
        assert close(po, ra6.bucket_prediction(setup, lm, td, c, H, row['seg_fpr_pred'])), (t, f)
        if p6 is not None:
            assert close(po, p6), (t, f, po, p6)
        rows.append([t, f, p4, po, pc, meas])
    return rows


def seeds(ds, kib):
    setup, scores, _ = E5.load(ds)
    specs = dict(E5.workload_specs(len(setup.h1q)))
    src = json.loads((R6 / 'results' / 'e3_seeds' / f'{ds}_{kib}.json').read_text(encoding='utf-8'))
    dest = ROOT / 'results' / f'seeds_{ds}_{kib}.json'
    out = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else []
    done = {(r['workload'], r['seed']) for r in out}
    for rec in src:
        if (rec['workload'], rec['seed']) in done:
            continue
        base = E5.base_stream(setup, rec['workload'], specs[rec['workload']], rec['seed'])
        n = len(base) // 4
        lm = RA.ra4.summarize(base[:n], True)
        rows = rescore(setup, scores, lm, kib, len(base) - n, rec['rank_rows'])
        out.append(dict(workload=rec['workload'], seed=rec['seed'], rows=rows))
        dest.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
        print(ds, kib, rec['workload'], rec['seed'], flush=True)


def holdout():
    ds = 'mawi2024_flow'
    setup, scores, _ = E5.load(ds)
    src = json.loads((R6 / 'results' / 'holdout' / 'e3_holdout.json').read_text())
    base = E5.base_stream(setup, '真实轨迹', None, 0)
    n = len(base) // 4
    lm = RA.ra4.summarize(base[:n], True)
    out = []
    for rec in src:
        rows = rescore(setup, scores, lm, rec['budget_kib'], len(base) - n, rec['rows'])
        out.append(dict(budget_kib=rec['budget_kib'], rows=rows))
        print(ds, rec['budget_kib'], len(rows), flush=True)
    (ROOT / 'results' / 'holdout_mawi2024_flow.json').write_text(json.dumps(out), encoding='utf-8')


if __name__ == '__main__':
    (ROOT / 'results').mkdir(exist_ok=True)
    if sys.argv[1] == 'seeds':
        seeds(sys.argv[2], int(sys.argv[3]))
    else:
        holdout()

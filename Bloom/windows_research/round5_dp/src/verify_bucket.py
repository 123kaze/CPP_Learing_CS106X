"""Offline check of option D on round-5 E3 data (development data only; not a method change yet).

For each E3 case, take RA4's `top` candidates by its own prediction, build each one, and
re-predict its tail FP from the *actual* bucket load: the learning-period keys that are FPs of
that structure are hashed with cache5's bucket function, and every bucket gets its own Che
characteristic time from its own keys' rates (4 slots per bucket).  Unseen-key mass keeps the
expected treatment (eps_i * G_i), spread evenly over buckets.  The D choice is the candidate
with the smallest D prediction; it is compared with RA4's choice, the measured best in the
table, and LearnGrid (from rows_*.csv).
usage: verify_bucket.py <e3 jsonl> [top]
"""
import csv
import json
import sys
from pathlib import Path
import numpy as np
import engine5 as E5
import ra5 as RA

ROOT = Path(__file__).resolve().parents[1]
WAYS = E5.WAYS


def buckets_of(h, B, P=40):
    Q = min(P, 32)
    x = (np.asarray(h, np.uint64) >> np.uint64(64 - Q))
    return ((x * np.uint64(B)) >> np.uint64(Q)).astype(np.int64)


def bucket_che(lam, b, B, H, g_new, iters=60):
    """Per-bucket Che: T_b with sum_k (1 - exp(-lam_k * min(T,H))) + g_new*min(T,H) = WAYS."""
    lo = np.zeros(B)
    hi = np.full(B, np.log(1e3 * H))
    cnt = np.bincount(b, minlength=B)
    for _ in range(iters):
        mid = (lo + hi) / 2
        T = np.minimum(np.exp(mid), H)
        occ = np.bincount(b, 1 - np.exp(-lam * T[b]), minlength=B) + g_new * T
        over = occ > WAYS
        hi = np.where(over, mid, hi)
        lo = np.where(over, lo, mid)
    T = np.exp(lo)
    T = np.where((cnt <= WAYS) & (g_new * H <= WAYS - cnt), 1e3 * H, T)   # bucket can hold everything
    a = 1 - np.exp(-lam * H)
    return float((a + np.maximum(0, lam * H - a) * np.exp(-lam * T[b])).sum())


def main(path, top=10):
    path = Path(path)
    ds, kib = path.stem[3:].rsplit('_', 1)
    kib = int(kib)
    budget = kib * 1024
    setup, scores, safe = E5.load(ds)
    specs = dict(E5.workload_specs(len(setup.h1q))) if not ds.endswith('_flow') else {'真实轨迹': None}
    rows = {(r['workload'], r['method']): r for r in csv.DictReader(open(ROOT / 'results' / f'rows_{ds}_{kib}.csv', encoding='utf-8'))
            if r['seed'] == '0'}
    cfg = RA.Config(new_mix=0.)
    out = []
    for line in path.read_text(encoding='utf-8').splitlines():
        rec = json.loads(line)
        if rec['workload'] == E5.PROBE:
            continue                      # tail depends on the structure (F-C); learning has no replays
        base = E5.base_stream(setup, rec['workload'], specs[rec['workload']], 0)
        n = len(base) // 4
        H = len(base) - n
        lm = RA.ra4.summarize(base[:n], True)
        cs = sorted(rec['candidates'], key=lambda c: (c['pred'], c['trees'], c['frac']))[:top]
        pops = {}
        for c in cs:
            t, frac = c['trees'], c['frac']
            td = E5.tree(setup, scores, t)
            if t not in pops:
                pops[t] = RA.population(lm, td, H, cfg)
            P = pops[t]
            cb, S = E5.cache_alloc(budget, frac)
            bits = (budget - td.fixed - cb) * 8
            e, _ = RA.ra4.solve(P, S, bits, 'ra', setassoc=True)
            w = RA.dp_weights(P, P.misses(e, S, True), td)
            st = E5.build(setup, scores, t, kib, frac, weights=w, cache_bytes=cb, slots=S)['structure']
            fpk = st.fp_static[lm.keys]
            lam = lm.rate[fpk]
            G = H * lm.N1 / lm.L * td.h                    # unseen-key tail queries per segment (NEW_MIX=0)
            new_miss = float((st.seg_fpr * G).sum())
            if cb == 0:
                c['pred_D'] = float((lam * H).sum()) + new_miss
                continue
            B = S // WAYS
            b = buckets_of(setup.h1q[lm.keys[fpk]], B)
            c['pred_D'] = bucket_che(lam, b, B, H, new_miss / H / B) + new_miss
        best_meas = min(c['measured'] for c in rec['candidates'])
        pick = lambda key, k: min(cs[:k], key=lambda c: (c[key], c['trees'], c['frac']))  # noqa: E731
        res = dict(workload=rec['workload'], best_measured=best_meas,
                   ra4=int(rows[rec['workload'], 'RA4']['fp_tail']), grid=int(rows[rec['workload'], 'LearnGrid']['fp_tail']),
                   ra4_table=cs[0]['measured'],
                   D3=pick('pred_D', 3)['measured'], D5=pick('pred_D', 5)['measured'], D10=pick('pred_D', 10)['measured'],
                   best_in_top10=min(c['measured'] for c in cs),
                   rank_rows=[(c['trees'], c['frac'], round(c['pred']), round(c['pred_D']), c['measured']) for c in cs])
        out.append(res)
        print(ds, kib, rec['workload'], {k: res[k] for k in ('grid', 'ra4', 'D3', 'D5', 'D10', 'best_in_top10', 'best_measured')}, flush=True)
    dest = ROOT / 'results' / 'verify_bucket'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f'{ds}_{kib}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10)

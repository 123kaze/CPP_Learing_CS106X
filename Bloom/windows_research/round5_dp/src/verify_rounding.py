"""Diagnosis: does the rounding of Bloom parameters explain RA4's ranking errors?

ra5 predicts each candidate with the DP's continuous region FPRs f_r, but the deployed Bloom
filters use m = floor(bpm*n) bits and k = rint(bpm*ln2) hashes.  For every E3 candidate (already
built and measured in round 5) this recomputes the prediction with
  pred_int: region FPR (1 - exp(-k*n/m))^k of the integer (m, k) actually deployed
  pred_bfk: C.bf_fpr(bpm) (integer k, continuous bits; what engine5 reports as seg_fpr)
and compares ranking quality with the stored measurements, grouped by key pool.
No evaluation segment is re-simulated; nothing here changes the frozen method.
usage: verify_rounding.py <e3 jsonl> [...]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
import engine5 as E5
import ra5 as RA
import dp_alloc as D

ROOT = Path(__file__).resolve().parents[1]
C = E5.C


def int_fprs(td, w, avail):
    M = float(avail)
    for _ in range(20):
        b, f, _ = D.allocate(td.g, w, M)
        reg_seg, n, bpm, m, kind = E5.region_bits(td, b, f)
        if m.sum() <= avail:
            break
        M *= avail / m.sum() * 0.9999
    k = np.where(kind == C.BF, np.maximum(1, np.rint(bpm * np.log(2))), 0)
    f_int = np.where(kind == C.PASS, 1., 0.)
    bf = kind == C.BF
    f_int[bf] = (1 - np.exp(-k[bf] * n[bf] / m[bf])) ** k[bf]
    f_bfk = np.where(kind == C.PASS, 1., np.where(bf, C.bf_fpr(np.maximum(bpm, 1e-9)), 0.))
    cont = np.where(n > 0, f, 0.)
    return f_int[reg_seg], f_bfk[reg_seg], cont[reg_seg]


def group(name):
    if name == '真实轨迹':
        return 'real'
    for p in ('1万', '10万', '100万', '全部'):
        if name.endswith('-' + p):
            return p
    return 'other'


def main(files):
    cfg = RA.Config(new_mix=0.)
    out = []
    for f in files:
        f = Path(f)
        ds, kib = f.stem[3:].rsplit('_', 1)
        kib = int(kib)
        setup, scores, safe = E5.load(ds)
        specs = dict(E5.workload_specs(len(setup.h1q))) if not ds.endswith('_flow') else {'真实轨迹': None}
        budget = kib * 1024
        for line in f.read_text(encoding='utf-8').splitlines():
            rec = json.loads(line)
            base = E5.base_stream(setup, rec['workload'], specs[rec['workload']], rec['seed'])
            n = len(base) // 4
            H = len(base) - n
            lm = RA.ra4.summarize(base[:n], True)
            pops = {}
            res = []
            for c in rec['candidates']:
                t, frac = c['trees'], c['frac']
                td = E5.tree(setup, scores, t)
                if t not in pops:
                    pops[t] = RA.population(lm, td, H, cfg)
                P = pops[t]
                cb, S = E5.cache_alloc(budget, frac)
                bits = (budget - td.fixed - cb) * 8
                e, _ = RA.ra4.solve(P, S, bits, 'ra', setassoc=True)
                w = RA.dp_weights(P, P.misses(e, S, True), td)
                fi, fb, fc = int_fprs(td, w, bits)
                res.append(dict(trees=t, frac=frac, measured=c['measured'], pred=c['pred'],
                                pred_check=float(fc @ P.misses(fc, S, True)),
                                pred_int=float(fi @ P.misses(fi, S, True)),
                                pred_bfk=float(fb @ P.misses(fb, S, True)),
                                min_k=None))
            out.append(dict(dataset=ds, budget_kib=kib, workload=rec['workload'], group=group(rec['workload']), candidates=res))
            print(ds, kib, rec['workload'], len(res), flush=True)
        E5._TREE.clear()
        E5.R._GSETUPS.clear()
    dest = ROOT / 'results' / 'verify_rounding'
    dest.mkdir(parents=True, exist_ok=True)
    name = '_'.join(Path(f).stem[3:] for f in files)[:80]
    (dest / f'{name}.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')


def summarize():
    recs = [r for f in sorted((ROOT / 'results' / 'verify_rounding').glob('*.json')) for r in json.loads(f.read_text(encoding='utf-8'))]
    stat = defaultdict(lambda: defaultdict(lambda: dict(rho=[], top1=[], top3=[], rel=[])))
    for r in recs:
        cs = r['candidates']
        if len(cs) < 3:
            continue
        meas = np.array([c['measured'] for c in cs], float)
        for p in ('pred', 'pred_int', 'pred_bfk'):
            pr = np.array([c[p] for c in cs], float)
            for g in (r['group'], 'all'):
                s = stat[g][p]
                if np.ptp(pr) > 0 and np.ptp(meas) > 0:
                    s['rho'].append(spearmanr(pr, meas).statistic)
                o = np.argsort(pr, kind='stable')
                s['top1'].append(meas[o[0]] == meas.min())
                s['top3'].append(meas.min() in meas[o[:3]])
                ok = meas > 0
                s['rel'] += list(np.abs(pr[ok] - meas[ok]) / meas[ok])
    lines = ['| 分组 | 预测 | 案例 | Spearman 中位 | top-1 | top-3 | 相对误差中位 |', '|---|---|---:|---:|---:|---:|---:|']
    for g in ('1万', '10万', '100万', '全部', 'other', 'real', 'all'):
        for p, s in stat.get(g, {}).items():
            lines.append(f"| {g} | {p} | {len(s['top1'])} | {np.median(s['rho']):.3f} | {np.mean(s['top1']):.0%} | "
                         f"{np.mean(s['top3']):.0%} | {np.median(s['rel']):.3f} |")
    check = [abs(c['pred'] - c['pred_check']) / max(c['pred'], 1) for r in recs for c in r['candidates']]
    lines.append(f'\n复算一致性：存档预测与复算的连续 FPR 预测，相对差最大 {max(check):.2e}（应为 0）。')
    text = '\n'.join(lines)
    (ROOT / 'results' / 'verify_rounding' / 'summary.md').write_text(text + '\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    if sys.argv[1] == '--summary':
        summarize()
    else:
        main(sys.argv[1:])

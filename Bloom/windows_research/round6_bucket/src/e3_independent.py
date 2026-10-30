"""E3 on independent data for the frozen RA6 predictor -> results/e3_independent.md

(a) synthetic seeds 1-4 (results/e3_seeds/*.json): RA4's top 10 built and measured;
    metrics inside the top 5 (what RA6 uses) plus top-5 recall of the best of the top 10;
(b) MAWI 2024 holdout (results/holdout/e3_holdout.json): every candidate built and measured.
Signed error = (pred - measured) / measured, to see whether the bias is systematic.
Cases whose best measured candidate has < MIN_REF false positives are reported separately.
"""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
MIN_REF = 30


def grp(w):
    for p in ('1万', '10万', '100万', '全部'):
        if w.endswith('-' + p):
            return p + ' key 池'
    return '每key一次/全新对抗'


def metrics(rows, k=5):
    """rows: [trees, frac, RA4 pred, bucket pred, measured] in RA4 order."""
    a = np.array([r[2:5] for r in rows], float)
    pr, pd, meas = a[:k, 0], a[:k, 1], a[:k, 2]
    out = {}
    if np.ptp(meas) > 0:
        if np.ptp(pr) > 0:
            out['rho_RA4'] = spearmanr(pr, meas).statistic
        if np.ptp(pd) > 0:
            out['rho_RA6'] = spearmanr(pd, meas).statistic
    out['pick_RA4'] = meas[0] == meas.min()
    out['pick_RA6'] = meas[np.argmin(pd)] == meas.min()
    ok = meas > 0
    out['err_RA4'] = list((pr[ok] - meas[ok]) / meas[ok])
    out['err_RA6'] = list((pd[ok] - meas[ok]) / meas[ok])
    out['recall5'] = a[:, 2].min() in meas
    return out


def table(S, title, note):
    L = [title, '', note, '',
         '| 分组 | 案例 | 前 5 内 Spearman RA4 → RA6 | 前 5 内选中最优 RA4 → RA6 | 相对误差中位 |误差| RA4 → RA6 | 带符号误差中位 RA4 → RA6 | 前 10 最优在前 5 |',
         '|---|---:|---:|---:|---:|---:|---:|']
    for g, ms in S.items():
        if not ms:
            continue
        get = lambda k: [m[k] for m in ms if k in m]  # noqa: E731
        ea4 = np.concatenate([m['err_RA4'] for m in ms]) if ms else np.array([])
        ea6 = np.concatenate([m['err_RA6'] for m in ms]) if ms else np.array([])
        L.append(f"| {g} | {len(ms)} | {np.median(get('rho_RA4')):.3f} → {np.median(get('rho_RA6')):.3f} | "
                 f"{np.mean(get('pick_RA4')):.0%} → {np.mean(get('pick_RA6')):.0%} | "
                 f"{np.median(np.abs(ea4)):.3f} → {np.median(np.abs(ea6)):.3f} | {np.median(ea4):+.3f} → {np.median(ea6):+.3f} | "
                 f"{np.mean(get('recall5')):.0%} |")
    return L + ['']


def main():
    S, Ssmall = defaultdict(list), defaultdict(list)
    for f in sorted((ROOT / 'results' / 'e3_seeds').glob('*.json')):
        for r in json.loads(f.read_text(encoding='utf-8')):
            m = metrics(r['rank_rows'])
            best = min(x[4] for x in r['rank_rows'])
            for g in (grp(r['workload']), '合计'):
                (S if best >= MIN_REF else Ssmall)[g].append(m)
    order = ['1万 key 池', '10万 key 池', '100万 key 池', '全部 key 池', '每key一次/全新对抗', '合计']
    S = {g: S[g] for g in order if g in S}
    Ssmall = {g: Ssmall[g] for g in order if g in Ssmall}
    L = ['# E3 独立证据：冻结的 RA6 预测器', '']
    L += table(S, f'## 合成负载，种子 1–4（方案 D 只在种子 0 上开发过），前 10 最优 ≥{MIN_REF}',
               '每个案例按 RA4 的预测取前 10 个候选，逐个建出结构、在评估段实测；指标在前 5 内计算（RA6 只在前 5 里选）。'
               '带符号误差 =（预测 − 实测）/ 实测，看偏差是否是系统性的。')
    L += table(Ssmall, f'## 同上，但前 10 最优 <{MIN_REF}（误报很少的案例，单列）', '')
    hd = ROOT / 'results' / 'holdout' / 'e3_holdout.json'
    if hd.exists():
        L += ['## MAWI 2024 独立验证集（全部候选都建出并实测）', '',
              '| 预算 | 候选数 | 全体 Spearman RA4 / RA6 | 全局最优在 RA4 前 5 | 前 5 内选中最优 RA4 → RA6 | 前 5 带符号误差中位 RA4 → RA6 |',
              '|---|---:|---:|---:|---:|---:|']
        for r in sorted(json.loads(hd.read_text()), key=lambda r: r['budget_kib']):
            rows = sorted(r['rows'], key=lambda x: (x[2], x[0], x[1]))
            a = np.array([x[2:5] for x in rows], float)
            rho4 = spearmanr(a[:, 0], a[:, 2]).statistic if np.ptp(a[:, 2]) > 0 else float('nan')
            rho6 = spearmanr(a[:, 1], a[:, 2]).statistic if np.ptp(a[:, 2]) > 0 else float('nan')
            m = metrics(rows)
            rec = a[:, 2].min() in a[:5, 2]
            L.append(f"| {r['budget_kib']}KiB | {len(rows)} | {rho4:.3f} / {rho6:.3f} | {'是' if rec else '否'} | "
                     f"{'是' if m['pick_RA4'] else '否'} → {'是' if m['pick_RA6'] else '否'} | "
                     f"{np.median(m['err_RA4']) if m['err_RA4'] else float('nan'):+.3f} → {np.median(m['err_RA6']) if m['err_RA6'] else float('nan'):+.3f} |")
        L.append('')
    (ROOT / 'results' / 'e3_independent.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

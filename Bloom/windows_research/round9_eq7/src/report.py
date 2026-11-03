"""results/seeds_*.json + results/holdout_mawi2024_flow.json -> results/report.md

Same cases, groups and MIN_REF split as round6_bucket/src/e3_independent.py.  Within RA4's top 5
(RA6's shortlist) for every case:
- signed / absolute relative error (pred - measured) / measured, original vs corrected;
- Spearman rank correlation with the measured tail FPs, and whether the pick is the measured best;
- whether the corrected formula picks a different candidate, and the measured FPs of the two picks
  (known for every shortlisted candidate, so no new simulation is needed).
"""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
MIN_REF = 30
K = 5
ORDER = ['1万 key 池', '10万 key 池', '100万 key 池', '全部 key 池', '每key一次/全新对抗', '合计']


def grp(w):
    for p in ('1万', '10万', '100万', '全部'):
        if w.endswith('-' + p):
            return p + ' key 池'
    return '每key一次/全新对抗'


def case(rows, k=K):
    """rows [trees, frac, RA4, orig, corr, meas] in RA4 order -> metrics inside the top k."""
    a = np.array([r[2:6] for r in rows], float)[:k]
    po, pc, m = a[:, 1], a[:, 2], a[:, 3]
    io, ic = int(np.argmin(po)), int(np.argmin(pc))   # first minimum, as min() in ra6.select6_multi
    out = dict(pick_o=m[io] == m.min(), pick_c=m[ic] == m.min(), changed=io != ic,
               fp_o=m[io], fp_c=m[ic], best=m.min(), sum_po=po.sum(), sum_pc=pc.sum(), sum_m=m.sum())
    if np.ptp(m) > 0:
        if np.ptp(po) > 0:
            out['rho_o'] = spearmanr(po, m).statistic
        if np.ptp(pc) > 0:
            out['rho_c'] = spearmanr(pc, m).statistic
    ok = m > 0
    out['err_o'] = list((po[ok] - m[ok]) / m[ok])
    out['err_c'] = list((pc[ok] - m[ok]) / m[ok])
    return out


def table(S):
    L = ['| 分组 | 案例 | 带符号误差中位 原式 → 修正 | 相对误差中位 原式 → 修正 | 预测总和/实测总和 原式 → 修正 | '
         'Spearman 中位 原式 → 修正 | 选中最优 原式 → 修正 | 选择改变 | 实测误报 修正选择/原选择 |',
         '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for g in ORDER:
        ms = S.get(g)
        if not ms:
            continue
        eo = np.concatenate([x['err_o'] for x in ms])
        ec = np.concatenate([x['err_c'] for x in ms])
        get = lambda k: [x[k] for x in ms if k in x]  # noqa: E731
        so, sc, sm = (sum(x[k] for x in ms) for k in ('sum_po', 'sum_pc', 'sum_m'))
        fo, fc = sum(x['fp_o'] for x in ms), sum(x['fp_c'] for x in ms)
        rho_o, rho_c = get('rho_o'), get('rho_c')
        L.append(f"| {g} | {len(ms)} | {np.median(eo):+.3f} → {np.median(ec):+.3f} | "
                 f"{np.median(np.abs(eo)):.3f} → {np.median(np.abs(ec)):.3f} | {so / sm:.3f} → {sc / sm:.3f} | "
                 f"{np.median(rho_o) if rho_o else float('nan'):.3f} → {np.median(rho_c) if rho_c else float('nan'):.3f} | "
                 f"{np.mean(get('pick_o')):.0%} → {np.mean(get('pick_c')):.0%} | {np.mean(get('changed')):.0%} | "
                 f"{fc / fo:.4f} |")
    return L


def main():
    S, Ssmall = defaultdict(list), defaultdict(list)
    files = sorted(ROOT.glob('results/seeds_*.json'))
    n_cand = 0
    for f in files:
        for r in json.loads(f.read_text(encoding='utf-8')):
            n_cand += len(r['rows'])
            m = case(r['rows'])
            best10 = min(x[5] for x in r['rows'])
            for g in (grp(r['workload']), '合计'):
                (S if best10 >= MIN_REF else Ssmall)[g].append(m)
    L = ['# 式 (7) 有限窗口修正：离线重算（E3 的同一批候选）', '',
         f'{len(files)} 个合成设置，种子 1–4，{len(S["合计"]) + len(Ssmall["合计"])} 个案例、{n_cand} 个已建出并实测过的候选。'
         '方法不变，只把 RA6 按实际桶负载的预测里的每 key 缺失数换成修正式；原式的预测逐个与 E3 存档一致（断言）。'
         f'指标都在 RA4 前 {K} 内（RA6 的短名单）。带符号误差 =（预测 − 实测）/ 实测。'
         '"实测误报 修正选择/原选择"是两种选择在评估段的实测误报总和之比，小于 1 表示修正后更好。', '',
         f'## 合成负载，前 10 最优 ≥{MIN_REF}', '']
    L += table(S) + ['', f'## 合成负载，前 10 最优 <{MIN_REF}（误报很少的案例，单列）', ''] + table(Ssmall) + ['']
    hd = ROOT / 'results' / 'holdout_mawi2024_flow.json'
    if hd.exists():
        L += ['## MAWI 2024 留出集（全部候选都建出并实测；此处只作诊断，见结论）', '',
              '| 预算 | 候选数 | 全体 Spearman 原式 / 修正 | 前 5 带符号误差中位 原式 → 修正 | 前 5 预测总和/实测总和 原式 → 修正 | '
              '前 5 内选中最优 原式 → 修正 | 选择改变 | 实测误报 修正选择/原选择 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
        for r in sorted(json.loads(hd.read_text()), key=lambda r: r['budget_kib']):
            rows = sorted(r['rows'], key=lambda x: (x[2], x[0], x[1]))
            a = np.array([x[2:6] for x in rows], float)
            rho = [spearmanr(a[:, j], a[:, 3]).statistic if np.ptp(a[:, 3]) > 0 else float('nan') for j in (1, 2)]
            m = case(rows)
            L.append(f"| {r['budget_kib']}KiB | {len(rows)} | {rho[0]:.3f} / {rho[1]:.3f} | "
                     f"{np.median(m['err_o']):+.3f} → {np.median(m['err_c']):+.3f} | "
                     f"{m['sum_po'] / m['sum_m']:.3f} → {m['sum_pc'] / m['sum_m']:.3f} | "
                     f"{'是' if m['pick_o'] else '否'} → {'是' if m['pick_c'] else '否'} | {'是' if m['changed'] else '否'} | "
                     f"{m['fp_c'] / m['fp_o']:.4f} |")
        L.append('')
    (ROOT / 'results' / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

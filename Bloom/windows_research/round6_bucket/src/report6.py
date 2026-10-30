"""Round-6 report: RA6 (option D) vs round-5 rows on identical (dataset, budget, workload, seed).

Only cases present in both rounds are compared. Writes results/report.md.
"""
import csv
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R5 = ROOT.parent / 'round5_dp' / 'results'
ORDER = ['cod', 'caida', 'shalla', 'url', 'caida_flow', 'mawi2020_flow', 'mawi2021_flow', 'mawi2022_flow']
HIGH = {'cod': 4096, 'caida': 2048, 'shalla': 4096, 'caida_flow': 256, 'mawi2020_flow': 128,
        'mawi2021_flow': 128, 'mawi2022_flow': 128}
NOREP = ('每key一次', '全新对抗')


def ratio(a, b):
    return (a + 1) / (b + 1)


def load(d, tag=''):
    out = defaultdict(dict)
    for f in sorted((d / tag).glob('rows_*.csv') if tag else d.glob('rows_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            out[r['dataset'], int(r['budget_kib']), r['workload'], int(r['seed'])][r['method']] = r
    return out


def group(w):
    if w == '真实轨迹':
        return '真实轨迹'
    for p in ('1万', '10万', '100万', '全部'):
        if w.endswith('-' + p):
            return p
    return '无重复/探测'


def main():
    r5, r6 = load(R5), load(ROOT / 'results', 'main')
    keys = sorted(k for k in r6 if k in r5 and 'LearnGrid' in r5[k])
    L = ['# 第六轮（RA6，按实际桶负载精算）对第五轮', '',
         f'对齐的案例：{len(keys)} 个（第五轮尚未完成的案例暂不比较）。比值都是 (误报+1)/(误报+1)。', '']
    # per-workload ratios
    G = defaultdict(lambda: defaultdict(list))
    norep_eq = norep_n = 0
    for k in keys:
        a, b = r5[k], r6[k]
        g = group(k[2])
        grid, gama, ra4 = (int(a[m]['fp_tail']) for m in ('LearnGrid', 'Gama', 'RA4'))
        orc = a['RA4']['fp_oracle']
        for m in ('RA6', 'RA6-top3', 'RA6-top10'):
            v = int(b[m]['fp_tail'])
            for gg in (g, '全部案例'):
                G[gg][m + '/网格'].append(ratio(v, grid))
                G[gg][m + '/RA4'].append(ratio(v, ra4))
                G[gg][m + '/Gama'].append(ratio(v, gama))
                if orc != '':
                    G[gg][m + '/最优'].append(ratio(v, float(orc)))
        for gg in (g, '全部案例'):
            G[gg]['RA4/网格'].append(ratio(ra4, grid))
            if orc != '':
                G[gg]['RA4/最优'].append(ratio(ra4, float(orc)))
                G[gg]['网格/最优'].append(ratio(grid, float(orc)))
        if k[2] in NOREP:
            norep_n += 1
            norep_eq += int(b['RA6']['fp_tail']) == int(a['Gama']['fp_tail'])
    L += ['## 逐案例比值（中位数 / 最坏 / ≤1 的比例）', '',
          '| 分组 | 案例 | RA4/网格 | **RA6/网格** | RA6/RA4 | RA6/Gama | RA4/最优 | RA6/最优 | 网格/最优 | RA6-top3/网格 | RA6-top10/网格 |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']

    def cell(v):
        v = np.array(v)
        return f'{np.median(v):.3f} / {v.max():.2f} / {np.mean(v <= 1):.0%}' if len(v) else '—'
    for g in ('1万', '10万', '100万', '全部', '无重复/探测', '真实轨迹', '全部案例'):
        s = G.get(g)
        if not s:
            continue
        L.append(f"| {g} | {len(s['RA6/网格'])} | {cell(s['RA4/网格'])} | **{cell(s['RA6/网格'])}** | {cell(s['RA6/RA4'])} | "
                 f"{cell(s['RA6/Gama'])} | {cell(s['RA4/最优'])} | {cell(s['RA6/最优'])} | {cell(s['网格/最优'])} | "
                 f"{cell(s['RA6-top3/网格'])} | {cell(s['RA6-top10/网格'])} |")
    L += ['', f'无重复负载上 RA6 与 Gama 逐位相同：{norep_eq}/{norep_n}。', '']
    # per-setting totals
    L += ['## 按设置的尾段误报总量（只含两轮都完成的案例；种子均值后对负载求和）', '',
          '| 设置 | 负载 | Gama | 网格 | RA4 | **RA6** | RA6/网格 | RA6/RA4 | RA6/Gama |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    S = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for k in keys:
        for m in ('Gama', 'LearnGrid', 'RA4'):
            S[k[:2]][k[2]][m].append(int(r5[k][m]['fp_tail']))
        S[k[:2]][k[2]]['RA6'].append(int(r6[k]['RA6']['fp_tail']))
    crit = dict(n=0, gama=0, grid_total=0, grid_med=0)
    for (ds, kib) in sorted(S, key=lambda x: (ORDER.index(x[0]), x[1])):
        ws = S[ds, kib]
        tot = {m: sum(np.mean(ws[w][m]) for w in ws) for m in ('Gama', 'LearnGrid', 'RA4', 'RA6')}
        med = np.median([ratio(np.mean(ws[w]['RA6']), np.mean(ws[w]['LearnGrid'])) for w in ws])
        crit['n'] += 1
        crit['gama'] += tot['RA6'] <= 1.01 * tot['Gama']
        crit['grid_total'] += tot['RA6'] <= tot['LearnGrid']
        crit['grid_med'] += med <= 1
        star = ' ★' if HIGH.get(ds) == kib else ''
        L.append(f"| {ds} {kib}{star} | {len(ws)} | {tot['Gama']:,.0f} | {tot['LearnGrid']:,.0f} | {tot['RA4']:,.0f} | "
                 f"**{tot['RA6']:,.0f}** | {ratio(tot['RA6'], tot['LearnGrid']):.3f} | {ratio(tot['RA6'], tot['RA4']):.3f} | "
                 f"{ratio(tot['RA6'], tot['Gama']):.3f} |")
    L += ['', '**E1 过关标准（RA6，只含已对齐的案例）**', '',
          f"- 按总量不比 Gama 差超过 1%：{crit['gama']}/{crit['n']}。",
          f"- 无重复负载上与 Gama 逐位一致：{norep_eq}/{norep_n}。",
          f"- 对网格：按总量不差 {crit['grid_total']}/{crit['n']}；各设置逐负载中位数 ≤1 的 {crit['grid_med']}/{crit['n']}；"
          f"全部案例的中位数 {np.median(G['全部案例']['RA6/网格']):.3f}。", '']
    sel = [float(r6[k]['RA6']['t_select_s']) for k in keys]
    L += [f'RA6 选择时间（含建 5 个结构，多进程并行下测得，仅供参考）：中位 {np.median(sel):.2f} 秒，90 分位 {np.quantile(sel, .9):.2f} 秒。正式计时见 E4。']
    (ROOT / 'results' / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

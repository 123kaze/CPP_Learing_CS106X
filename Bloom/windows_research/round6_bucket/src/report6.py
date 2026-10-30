"""Round-6 report: RA6 (option D) vs round-5 rows on identical (dataset, budget, workload, seed).

Reporting rules (decided before looking at round-6 numbers by setting):
  * the main tables exclude the probe-replay workload; it is reported separately as a
    robustness experiment (learning period has no replays, the evaluation segment does);
  * per-case ratios (fp+1)/(fp+1) only use cases whose reference -- the hindsight oracle when
    available (seeds 0-2), otherwise LearnGrid -- has at least MIN_REF false positives; the
    number of excluded cases is reported;
  * totals are seed means summed over workloads, all cases included.
Writes results/report.md.
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
PROBE = '探测重放10%'
MIN_REF = 30


def ratio(a, b):
    return (a + 1) / (b + 1)


def load(d):
    out = defaultdict(dict)
    for f in sorted(d.glob('rows_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            out[r['dataset'], int(r['budget_kib']), r['workload'], int(r['seed'])][r['method']] = r
    return out


def fp(rows, m):
    return int(rows[m]['fp_tail'])


def group(w):
    if w == '真实轨迹':
        return '真实轨迹'
    if w == PROBE:
        return '探测重放'
    for p in ('1万', '10万', '100万', '全部'):
        if w.endswith('-' + p):
            return p
    return '每key一次/全新对抗'


def ref(a):
    o = a['RA4']['fp_oracle']
    return float(o) if o != '' else float(fp(a, 'LearnGrid'))


def cell(v):
    v = np.array(v)
    return f'{np.median(v):.3f} / {v.max():.2f} / {np.mean(v <= 1):.0%}' if len(v) else '—'


def main():
    r5, r6 = load(R5), load(ROOT / 'results' / 'main')
    keys = sorted(k for k in r6 if k in r5 and 'LearnGrid' in r5[k])
    main_keys = [k for k in keys if k[2] != PROBE]
    L = ['# 第六轮（RA6，按实际桶负载精算）结果', '',
         f'对齐的案例共 {len(keys)} 个：RA6 来自第六轮；基线、RA4 和事后最优来自第五轮，流完全相同。',
         f'主表不含探测重放（单列在后面）。逐案例比值只统计参照值（有事后最优时用事后最优，否则用网格）≥{MIN_REF} 的案例。', '']

    # ---- per-case ratios, main workloads
    G = defaultdict(lambda: defaultdict(list))
    excluded = defaultdict(int)
    for k in main_keys:
        a, b = r5[k], r6[k]
        g = group(k[2])
        if ref(a) < MIN_REF:
            excluded[g] += 1
            excluded['全部（不含探测重放）'] += 1
            continue
        grid, gama, ra4, ra6 = fp(a, 'LearnGrid'), fp(a, 'Gama'), fp(a, 'RA4'), fp(b, 'RA6')
        orc = a['RA4']['fp_oracle']
        for gg in (g, '全部（不含探测重放）'):
            s = G[gg]
            s['RA4/网格'].append(ratio(ra4, grid))
            s['RA6/网格'].append(ratio(ra6, grid))
            s['RA6/RA4'].append(ratio(ra6, ra4))
            s['RA6/Gama'].append(ratio(ra6, gama))
            s['RA6-top3/网格'].append(ratio(fp(b, 'RA6-top3'), grid))
            s['RA6-top10/网格'].append(ratio(fp(b, 'RA6-top10'), grid))
            if orc != '':
                s['RA6/最优'].append(ratio(ra6, float(orc)))
                s['RA4/最优'].append(ratio(ra4, float(orc)))
                s['网格/最优'].append(ratio(grid, float(orc)))
    L += ['## 一、逐案例比值（不含探测重放；中位数 / 最坏 / ≤1 的比例）', '',
          '| 分组 | 计入 | 排除 | RA4/网格 | **RA6/网格** | RA6/RA4 | RA6/Gama | RA4/最优 | RA6/最优 | 网格/最优 | RA6-top3/网格 | RA6-top10/网格 |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for g in ('1万', '10万', '100万', '全部', '每key一次/全新对抗', '真实轨迹', '全部（不含探测重放）'):
        s = G.get(g)
        if not s:
            continue
        L.append(f"| {g} | {len(s['RA6/网格'])} | {excluded[g]} | {cell(s['RA4/网格'])} | **{cell(s['RA6/网格'])}** | "
                 f"{cell(s['RA6/RA4'])} | {cell(s['RA6/Gama'])} | {cell(s['RA4/最优'])} | {cell(s['RA6/最优'])} | "
                 f"{cell(s['网格/最优'])} | {cell(s['RA6-top3/网格'])} | {cell(s['RA6-top10/网格'])} |")
    norep = [k for k in main_keys if k[2] in NOREP]
    norep_eq = sum(fp(r6[k], 'RA6') == fp(r5[k], 'Gama') for k in norep)
    L += ['', f'无重复负载（每key一次、全新对抗）上 RA6 与 Gama 逐位相同：{norep_eq}/{len(norep)}（所有案例，不受 ≥{MIN_REF} 规则影响）。', '']

    # ---- totals per setting, main workloads
    S = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for k in main_keys:
        for m in ('Gama', 'LearnGrid', 'RA4'):
            S[k[:2]][k[2]][m].append(fp(r5[k], m))
        S[k[:2]][k[2]]['RA6'].append(fp(r6[k], 'RA6'))
    L += ['## 二、按设置的尾段误报总量（不含探测重放；种子均值后对负载求和）', '',
          '| 设置 | 负载 | Gama | 网格 | RA4 | **RA6** | RA6/网格 | RA6/RA4 | RA6/Gama |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    crit = dict(n=0, gama=0, grid=0)
    for (ds, kib) in sorted(S, key=lambda x: (ORDER.index(x[0]), x[1])):
        ws = S[ds, kib]
        tot = {m: sum(np.mean(ws[w][m]) for w in ws) for m in ('Gama', 'LearnGrid', 'RA4', 'RA6')}
        crit['n'] += 1
        crit['gama'] += tot['RA6'] <= 1.01 * tot['Gama']
        crit['grid'] += tot['RA6'] <= tot['LearnGrid']
        star = ' ★' if HIGH.get(ds) == kib else ''
        L.append(f"| {ds} {kib}{star} | {len(ws)} | {tot['Gama']:,.0f} | {tot['LearnGrid']:,.0f} | {tot['RA4']:,.0f} | "
                 f"**{tot['RA6']:,.0f}** | {ratio(tot['RA6'], tot['LearnGrid']):.3f} | {ratio(tot['RA6'], tot['RA4']):.3f} | "
                 f"{ratio(tot['RA6'], tot['Gama']):.3f} |")
    allr = np.array(G['全部（不含探测重放）']['RA6/网格'])
    L += ['', '**E1 过关标准（RA6，不含探测重放）**', '',
          f"- 按总量不比 Gama 差超过 1%：{crit['gama']}/{crit['n']}。",
          f"- 无重复负载上与 Gama 逐位一致：{norep_eq}/{len(norep)}。",
          f"- 对网格：逐案例中位数 {np.median(allr):.3f}（{len(allr)} 个案例，≤1 的 {np.mean(allr <= 1):.0%}）；按总量不差的设置 {crit['grid']}/{crit['n']}。", '']

    # ---- probe replay as robustness
    pk = [k for k in keys if k[2] == PROBE]
    P = defaultdict(lambda: defaultdict(list))
    for k in pk:
        for m in ('Gama', 'LearnGrid', 'RA4'):
            P[k[:2]][m].append(fp(r5[k], m))
        P[k[:2]]['RA6'].append(fp(r6[k], 'RA6'))
    L += ['## 三、稳健性：对称探测重放（单列）', '',
          '学习期不含重放；到了评估段，每个结构以 10% 的概率重放它自己已经被观察到的误报 key。所以选择阶段看不到这种攻击，结果主要取决于选中的结构有没有留下足够的缓存来吸收重放。这衡量的是"学习期与评估段不一致"时的稳健性，不是方法的核心优势。', '',
          '| 设置 | 种子 | Gama | 网格 | RA4 | RA6 | RA6/网格 | RA6/RA4 |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for (ds, kib) in sorted(P, key=lambda x: (ORDER.index(x[0]), x[1])):
        p = {m: np.mean(v) for m, v in P[ds, kib].items()}
        L.append(f"| {ds} {kib} | {len(P[ds, kib]['RA6'])} | {p['Gama']:,.0f} | {p['LearnGrid']:,.0f} | {p['RA4']:,.0f} | "
                 f"{p['RA6']:,.0f} | {ratio(p['RA6'], p['LearnGrid']):.3f} | {ratio(p['RA6'], p['RA4']):.3f} |")
    worse = sorted(((ratio(fp(r6[k], 'RA6'), fp(r5[k], 'RA4')), k, fp(r6[k], 'RA6'), fp(r5[k], 'RA4'), fp(r5[k], 'LearnGrid'))
                    for k in pk), reverse=True)[:5]
    L += ['', 'RA6 相对 RA4 退步最大的探测重放案例。D 按学习期的误报 key 精算，而学习期没有重放：', '']
    L += [f'- {k[0]} {k[1]} 种子 {k[3]}：RA6 {a:,}，RA4 {b:,}，网格 {c:,}（{r:.1f}×）' for r, k, a, b, c in worse]
    L.append('')

    # ---- holdout
    hd, h5 = load(ROOT / 'results' / 'holdout'), load(ROOT / 'results' / 'holdout' / 'round5_methods')
    if hd:
        L += ['## 四、独立验证集 MAWI 2024（预先声明，冻结后只运行一次）', '',
              '| 预算 | Gama | 网格 | 事后最优 | RA4 | **RA6** | RA6/网格 |', '|---|---:|---:|---:|---:|---:|---:|']
        for k in sorted(hd, key=lambda x: x[1]):
            a, b = h5[k], hd[k]
            L.append(f"| {k[1]}KiB | {fp(a, 'Gama'):,} | {fp(a, 'LearnGrid'):,} | {float(a['RA4']['fp_oracle']):,.0f} | {fp(a, 'RA4'):,} | "
                     f"**{fp(b, 'RA6'):,}** | {ratio(fp(b, 'RA6'), fp(a, 'LearnGrid')):.3f} |")
        L += ['', 'Gama 在 24KiB 的误报（400,523）多于 16KiB（360,084）。可能的原因（未单独验证）：Gama 按验证集上估计的 FPR 选树数和分段，'
              '而验证集是均匀抽取的负例，和这条按时间排列、热点集中的查询流分布不同；多给内存时选出的配置在验证集上更好，在这条流上却更差。'
              '要确认，需要对比两个预算下选出的树数，以及验证集估计 FPR 和流上实测 FPR 的差距。', '']
    (ROOT / 'results' / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

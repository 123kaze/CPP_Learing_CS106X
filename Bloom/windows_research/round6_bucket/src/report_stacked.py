"""Learned stacked (round-5 engine, full workload set) vs RA6 / RA6-warm / LearnGrid / Gama on identical cases.

RA6-warm (warm6.py) is RA6 with the cache warmed by the learning period, i.e. the same knowledge
learned stacked carries into deployment; cases without a warm row are skipped in its columns.

Same rules as report6.py: probe replay reported separately; per-case ratios (fp+1)/(fp+1) only on
cases whose reference (oracle for seeds 0-2, else LearnGrid) has >= MIN_REF FPs; totals are seed
means summed over workloads.  Writes results/stacked_report.md.
"""
import csv
from collections import defaultdict
from pathlib import Path
import numpy as np
import report6 as R6

ROOT = Path(__file__).resolve().parents[1]


def main():
    r5, r6 = R6.load(R6.R5), R6.load(ROOT / 'results' / 'main')
    st = {}
    for f in sorted((ROOT / 'results' / 'stacked').glob('rows_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            st[r['dataset'], int(r['budget_kib']), r['workload'], int(r['seed'])] = r
    wm = {}
    for f in sorted((ROOT / 'results' / 'warm').glob('rows_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            wm[r['dataset'], int(r['budget_kib']), r['workload'], int(r['seed'])] = int(r['fp_tail'])
    keys = sorted(k for k in st if k in r5 and k in r6 and 'RA6' in r6[k])
    missing = len(st) - len(keys)
    fs = lambda k: int(st[k]['fp_tail'])  # noqa: E731
    L = ['# learned stacked 的完整对照（第五轮引擎，全部负载、5 个种子）', '',
         f'对齐的案例 {len(keys)} 个（未对齐 {missing} 个），其中有 RA6-warm 结果的 {sum(k in wm for k in keys)} 个。'
         'learned stacked 来自 `results/stacked/`，RA6 来自第六轮主表，RA6-warm 来自 `results/warm/`，'
         '网格、Gama、事后最优来自第五轮，流完全相同。',
         'RA6-warm = RA6 的结构不变，缓存先在学习期上回放一遍再进入评估段，和 learned stacked 把学习期误报带进部署的做法对等。',
         f'比值 = (误报+1)/(误报+1)，只统计参照值 ≥{R6.MIN_REF} 的案例；探测重放单列。表中每格为"中位数 / 最坏 / 不差于对方的比例"。', '',
         '## 逐案例比值（不含探测重放）', '',
         '| 分组 | 案例 | stacked / RA6 | stacked / 网格 | stacked / Gama | stacked 比 RA6 少 10% 以上的案例 | stacked / RA6-warm | RA6-warm / RA6 |',
         '|---|---:|---|---|---|---:|---|---|']
    G = defaultdict(lambda: defaultdict(list))
    for k in keys:
        a, b = r5[k], r6[k]
        if R6.ref(a) < R6.MIN_REF:
            continue
        g = '探测重放' if k[2] == R6.PROBE else R6.group(k[2])
        for gg in (g, '合计（不含探测重放）') if g != '探测重放' else (g,):
            G[gg]['ra6'].append(R6.ratio(fs(k), R6.fp(b, 'RA6')))
            G[gg]['grid'].append(R6.ratio(fs(k), R6.fp(a, 'LearnGrid')))
            G[gg]['gama'].append(R6.ratio(fs(k), R6.fp(a, 'Gama')))
            if k in wm:
                G[gg]['warm'].append(R6.ratio(fs(k), wm[k]))
                G[gg]['wr'].append(R6.ratio(wm[k], R6.fp(b, 'RA6')))
    for g in ('1万', '10万', '100万', '全部', '每key一次/全新对抗', '真实轨迹', '合计（不含探测重放）', '探测重放'):
        if g not in G:
            continue
        v = G[g]
        L.append(f'| {g} | {len(v["ra6"])} | {R6.cell(v["ra6"])} | {R6.cell(v["grid"])} | {R6.cell(v["gama"])} | '
                 f'{int(np.sum(np.array(v["ra6"]) < 0.9))} | {R6.cell(v["warm"])} | {R6.cell(v["wr"])} |')

    L += ['', '## 每个设置的误报总量（种子平均，按负载求和，不含探测重放）', '',
          '| 设置 | Gama | 网格 | RA6 | RA6-warm | learned stacked | stacked / RA6 | stacked / RA6-warm |',
          '|---|---:|---:|---:|---:|---:|---:|---:|']
    tot = defaultdict(lambda: defaultdict(list))
    for k in keys:
        if k[2] == R6.PROBE:
            continue
        a, b = r5[k], r6[k]
        t = tot[k[0], k[1]]
        for m, v in (('Gama', R6.fp(a, 'Gama')), ('LearnGrid', R6.fp(a, 'LearnGrid')), ('RA6', R6.fp(b, 'RA6')), ('st', fs(k)),
                     ('warm', wm.get(k))):
            if v is not None:
                t[(k[2], m)].append(v)
    wins = wins_w = n_w = 0
    order = sorted(tot, key=lambda x: (R6.ORDER.index(x[0]), x[1]))
    for ds, kib in order:
        t = tot[ds, kib]
        s = {m: sum(np.mean(v) for (w, mm), v in t.items() if mm == m) for m in ('Gama', 'LearnGrid', 'RA6', 'st', 'warm')}
        full = sum(1 for (w, mm) in t if mm == 'warm') == sum(1 for (w, mm) in t if mm == 'st')
        r = (s['st'] + 1) / (s['RA6'] + 1)
        wins += r < 1
        rw = '—'
        if full:
            rw_v = (s['st'] + 1) / (s['warm'] + 1)
            wins_w += rw_v < 1
            n_w += 1
            rw = f'{rw_v:.3f}'
        star = ' ★' if R6.HIGH.get(ds) == kib else ''
        L.append(f'| {ds} {kib}{star} | {s["Gama"]:,.0f} | {s["LearnGrid"]:,.0f} | {s["RA6"]:,.0f} | '
                 f'{(f"{s['warm']:,.0f}" if full else "—")} | {s["st"]:,.0f} | {r:.3f} | {rw} |')
    L += ['', f'按误报总量，learned stacked 在 {wins}/{len(order)} 个设置上少于 RA6，'
          f'在有完整 RA6-warm 结果的 {n_w} 个设置中有 {wins_w} 个少于 RA6-warm。', '']

    # cases where stacked beats RA6 by >10%, grouped by setting and workload family
    L += ['## learned stacked 比 RA6 少 10% 以上的案例（参照值 ≥30，不含探测重放）', '',
          '| 设置 | 负载 | 种子数 | 比值中位数 | stacked 选的 frac / b2 |', '|---|---|---:|---:|---|']
    by = defaultdict(list)
    for k in keys:
        if k[2] == R6.PROBE or R6.ref(r5[k]) < R6.MIN_REF:
            continue
        x = R6.ratio(fs(k), R6.fp(r6[k], 'RA6'))
        if x < 0.9:
            by[k[0], k[1], k[2]].append((x, st[k]['frac'], st[k]['b2']))
    for (ds, kib, w), v in sorted(by.items(), key=lambda z: (R6.ORDER.index(z[0][0]), z[0][1], z[0][2])):
        L.append(f'| {ds} {kib} | {w} | {len(v)} | {np.median([x for x, _, _ in v]):.3f} | '
                 f'{", ".join(sorted({f"{f}/{b}" for _, f, b in v}))} |')
    if not by:
        L.append('| — | — | 0 | — | — |')
    (ROOT / 'results' / 'stacked_report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

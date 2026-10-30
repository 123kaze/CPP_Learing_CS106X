"""E12: confidence intervals and Wilcoxon signed-rank tests on the round-6 main table.

Data: round-6 RA6 rows and round-5 baseline rows on identical streams (probe replay excluded).
  * per (setting, workload) with 5 seeds: mean tail FP of RA6 / grid / Gama and a 95% t interval
    of the per-seed log ratio log((RA6+1)/(grid+1));
  * global Wilcoxon signed-rank tests on per-case log ratios (cases with reference >= MIN_REF),
    RA6 vs grid and RA6 vs Gama, overall and by group, two-sided and one-sided;
  * real traces: block bootstrap over the 100 windows of the E9 runs (RA6 vs grid).
Writes results/e12_stats.md.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
R5 = ROOT.parent / 'round5_dp' / 'results'
PROBE = '探测重放10%'
MIN_REF = 30
rng = np.random.default_rng(12)


def load(d):
    out = defaultdict(dict)
    for f in sorted(d.glob('rows_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            out[r['dataset'], int(r['budget_kib']), r['workload'], int(r['seed'])][r['method']] = r
    return out


def grp(w):
    if w == '真实轨迹':
        return '真实轨迹'
    for p in ('1万', '10万', '100万', '全部'):
        if w.endswith('-' + p):
            return p + ' key 池'
    return '每key一次/全新对抗'


def lr(a, b):
    return np.log((a + 1) / (b + 1))


def main():
    r5, r6 = load(R5), load(ROOT / 'results' / 'main')
    keys = [k for k in r6 if k in r5 and k[2] != PROBE]
    L = ['# E12：置信区间与符号秩检验', '',
         '比值 = (误报+1)/(误报+1)，在对数尺度上做检验。只计入参照值（有事后最优时用事后最优，否则用网格）≥30 的案例，探测重放除外。', '']
    # ---- Wilcoxon
    G = defaultdict(lambda: defaultdict(list))
    for k in keys:
        a, b = r5[k], r6[k]
        o = a['RA4']['fp_oracle']
        ref = float(o) if o != '' else float(a['LearnGrid']['fp_tail'])
        if ref < MIN_REF:
            continue
        ra6, grid, gama = (int(x) for x in (b['RA6']['fp_tail'], a['LearnGrid']['fp_tail'], a['Gama']['fp_tail']))
        for g in (grp(k[2]), '合计'):
            G[g]['grid'].append(lr(ra6, grid))
            G[g]['gama'].append(lr(ra6, gama))
    L += ['## Wilcoxon 符号秩检验（每个案例一个对数比值）', '',
          '| 分组 | 案例 | RA6 对网格：几何平均比值 | 双侧 p | 单侧 p（RA6 更好） | 单侧 p（RA6 更差） | RA6 对 Gama：几何平均比值 | 单侧 p（RA6 更好） |',
          '|---|---:|---:|---:|---:|---:|---:|---:|']
    order = ['1万 key 池', '10万 key 池', '100万 key 池', '全部 key 池', '每key一次/全新对抗', '真实轨迹', '合计']
    for g in order:
        s = G.get(g)
        if not s:
            continue
        x, y = np.array(s['grid']), np.array(s['gama'])
        def w(v, alt):
            v = v[v != 0]
            return stats.wilcoxon(v, alternative=alt).pvalue if len(v) >= 6 else float('nan')
        L.append(f"| {g} | {len(x)} | {np.exp(x.mean()):.3f} | {w(x, 'two-sided'):.2g} | {w(x, 'less'):.2g} | {w(x, 'greater'):.2g} | "
                 f"{np.exp(y.mean()):.3f} | {w(y, 'less'):.2g} |")
    L += ['', '无重复负载上 RA6 与 Gama 逐位相同，对 Gama 的比值全为 1，因此该组对 Gama 的检验没有意义。', '']
    # ---- per (setting, workload) t intervals
    S = defaultdict(list)
    for k in keys:
        a, b = r5[k], r6[k]
        S[k[0], k[1], k[2]].append(lr(int(b['RA6']['fp_tail']), int(a['LearnGrid']['fp_tail'])))
    rows = []
    for (ds, kib, wl), v in S.items():
        if len(v) < 5:
            continue
        v = np.array(v)
        m, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
        lo, hi = m - stats.t.ppf(.975, len(v) - 1) * se, m + stats.t.ppf(.975, len(v) - 1) * se
        rows.append((ds, kib, wl, np.exp(m), np.exp(lo), np.exp(hi)))
    better = sum(r[5] < 1 for r in rows)
    worse = sum(r[4] > 1 for r in rows)
    L += ['## 每个（设置，负载）在 5 个种子上的 95% 置信区间（RA6/网格，几何平均）', '',
          f'共 {len(rows)} 个组合：区间整体低于 1（RA6 更好）{better} 个，整体高于 1（RA6 更差）{worse} 个，其余 {len(rows) - better - worse} 个跨过 1。', '',
          '注意两点：', '',
          '- 每个组合只有 5 个种子，所以单个组合的 t 区间只能作为描述。精确符号检验在 n=5 时双侧 p 最小为 0.0625，单个组合不能在 0.05 水平上下结论，主要看上面的整体检验。',
          '- "全新对抗"负载是确定性的（每个种子都是同一条流），所以 5 个种子完全相同，区间宽度为 0，这些组合不是 5 次独立重复。', '',
          '区间整体高于 1 的组合：', '']
    L += [f'- {ds} {kib} {wl}：{g:.3f}（{lo:.3f}–{hi:.3f}）' for ds, kib, wl, g, lo, hi in sorted(rows, key=lambda r: -r[4]) if lo > 1][:15]
    L += ['', '区间整体低于 1 的组合（前 15 个）：', '']
    L += [f'- {ds} {kib} {wl}：{g:.3f}（{lo:.3f}–{hi:.3f}）' for ds, kib, wl, g, lo, hi in sorted(rows, key=lambda r: r[5]) if hi < 1][:15]
    # ---- real traces: block bootstrap over E9 windows
    L += ['', '## 真实轨迹：按窗口的块自助法（E9 的 100 个窗口，块长 10，2000 次重抽样）', '',
          '对评估段的时间窗口重抽样，衡量的是"同一结构在这条轨迹上"误报总量的抽样波动，不包括选择本身的不确定性。', '',
          '| 轨迹 | 网格 尾段误报 | RA6 尾段误报 | RA6/网格 | 95% 区间 |', '|---|---:|---:|---:|---:|']
    for f in sorted((ROOT / 'results' / 'e789').glob('*_flow_*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        g = np.array(d['methods']['LearnGrid']['e9']['fp_per_window'], float)
        r = np.array(d['methods']['RA6']['e9']['fp_per_window'], float)
        B, n = 10, len(g)
        starts = rng.integers(0, n - B + 1, size=(2000, n // B))
        idx = (starts[:, :, None] + np.arange(B)).reshape(2000, -1)
        boot = (r[idx].sum(1) + 1) / (g[idx].sum(1) + 1)
        lo, hi = np.quantile(boot, [.025, .975])
        L.append(f"| {d['dataset']} {d['budget_kib']}KiB | {int(g.sum()):,} | {int(r.sum()):,} | {(r.sum() + 1) / (g.sum() + 1):.3f} | {lo:.3f}–{hi:.3f} |")
    L.append('')
    (ROOT / 'results' / 'e12_stats.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

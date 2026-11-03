"""Round-10 report: RA6 with the index-free 64-bit fingerprint cache vs index-based RA6 and Gama.

Same cases and rules as round6_bucket/src/report6.py: identical (dataset, budget, workload, seed);
the main tables exclude probe replay; per-case ratios (fp+1)/(fp+1) only use cases whose round-6
reference (hindsight oracle when available, otherwise LearnGrid) has >= MIN_REF FPs; totals are
seed means summed over workloads.  Writes results/report.md.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R6 = ROOT.parent / 'round6_bucket'
sys.path.insert(0, str(R6 / 'src'))
from report6 import ORDER, HIGH, NOREP, PROBE, MIN_REF, ratio, load, fp, group, ref, cell, R5  # noqa: E402

GROUPS = ('1万', '10万', '100万', '全部', '每key一次/全新对抗', '真实轨迹', '全部（不含探测重放）')

def decompose_section(r10, keys):
    """results/decompose: RA6's own (index-selected) structure with three equal-size caches."""
    rows = {}
    for f in sorted((ROOT / 'results' / 'decompose').glob('rows_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            rows[r['dataset'], int(r['budget_kib']), r['workload'], int(r['seed'])] = r
    if not rows:
        return []
    G = defaultdict(lambda: defaultdict(list))
    slots = []
    for k, r in rows.items():
        if k[2] == PROBE:
            gs = ('探测重放',)
        else:
            gs = (group(k[2]), GROUPS[-1])
        a, b, c = int(r['fp_idx']), int(r['fp_p40']), int(r['fp_fp64'])
        if int(r['slots_idx']):
            slots.append(int(r['slots_fp64']) / int(r['slots_idx']))
        if max(a, b, c) < MIN_REF:
            continue
        for g in gs:
            s = G[g]
            s['p40/idx'].append(ratio(b, a))
            s['fp64/p40'].append(ratio(c, b))
            s['fp64/idx'].append(ratio(c, a))
            if k in r10:
                s['sel/idx'].append(ratio(fp(r10[k], 'RA6-fp64'), a))
    L = ['## 五、差距从哪里来：同一个结构、同样字节的三种缓存', '',
         f'对第六轮 RA6 选出的结构（带索引选择，{len(rows)} 个案例，idx 的误报逐个复现第六轮），用同样的缓存字节换三种缓存：'
         'idx = 带索引的原缓存（按安全前缀匹配，一个条目也挡住同前缀的其他负例）；'
         'p40 = 同样布局和槽位数，但都按完整 40 位匹配（没有前缀泛化；仅作诊断）；'
         'fp64 = 64 位指纹缓存。idx → p40 是前缀泛化的作用，p40 → fp64 是槽位变少的作用；'
         '最后一列是第十轮按指纹缓存重新选配置的 RA6-fp64。',
         f'同样字节下 fp64 的槽位数是 idx 的 {np.median(slots):.1%}（中位，范围 {min(slots):.1%}–{max(slots):.1%}）。'
         f'只统计三者中最大误报 ≥{MIN_REF} 的案例；(误报+1)/(误报+1)，中位数 / 最坏 / ≤1 的比例。', '',
         '| 分组 | 计入 | 前缀泛化 p40 / idx | 槽位变少 fp64 / p40 | 合计 fp64 / idx（配置不变） | RA6-fp64（重新选） / idx |',
         '|---|---:|---:|---:|---:|---:|']
    for g in GROUPS + ('探测重放',):
        s = G.get(g)
        if s:
            L.append(f"| {g} | {len(s['p40/idx'])} | {cell(s['p40/idx'])} | {cell(s['fp64/p40'])} | {cell(s['fp64/idx'])} | "
                     f"{cell(s['sel/idx'])} |")
    return L + ['']


def main():
    r5, r6, r10 = load(R5), load(R6 / 'results' / 'main'), load(ROOT / 'results' / 'main')
    keys = sorted(k for k in r10 if k in r6 and k in r5 and 'LearnGrid' in r5[k])
    main_keys = [k for k in keys if k[2] != PROBE]
    G = defaultdict(lambda: defaultdict(list))
    excluded = defaultdict(int)
    for k in main_keys:
        a, b, c = r5[k], r6[k], r10[k]
        g = group(k[2])
        if ref(a) < MIN_REF:
            excluded[g] += 1
            excluded[GROUPS[-1]] += 1
            continue
        x, y, gama, grid = fp(c, 'RA6-fp64'), fp(b, 'RA6'), fp(a, 'Gama'), fp(a, 'LearnGrid')
        for gg in (g, GROUPS[-1]):
            s = G[gg]
            s['fp64/RA6'].append(ratio(x, y))
            s['fp64/Gama'].append(ratio(x, gama))
            s['RA6/Gama'].append(ratio(y, gama))
            s['fp64/网格'].append(ratio(x, grid))
    L = ['# 第十轮：不用成员索引的 64 位指纹缓存（RA6-fp64）', '',
         f'对齐的案例共 {len(keys)} 个，与第六轮主表的数据集、预算、负载、种子和查询流完全相同。'
         'RA6（带索引）来自第六轮，Gama 和网格来自第五轮；网格用的是带索引的缓存。'
         f'主表不含探测重放。逐案例比值 = (误报+1)/(误报+1)，只统计第六轮参照值 ≥{MIN_REF} 的案例。', '',
         '## 一、逐案例比值（中位数 / 最坏 / ≤1 的比例）', '',
         '| 分组 | 计入 | 排除 | **RA6-fp64 / RA6** | RA6-fp64 / Gama | RA6 / Gama | RA6-fp64 / 网格 |',
         '|---|---:|---:|---:|---:|---:|---:|']
    for g in GROUPS:
        s = G.get(g)
        if s:
            L.append(f"| {g} | {len(s['fp64/RA6'])} | {excluded[g]} | **{cell(s['fp64/RA6'])}** | {cell(s['fp64/Gama'])} | "
                     f"{cell(s['RA6/Gama'])} | {cell(s['fp64/网格'])} |")
    norep = [k for k in main_keys if k[2] in NOREP]
    eq = sum(fp(r10[k], 'RA6-fp64') == fp(r5[k], 'Gama') for k in norep)
    L += ['', f'无重复负载上 RA6-fp64 与 Gama 逐位相同：{eq}/{len(norep)}。', '']

    S = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for k in main_keys:
        S[k[:2]][k[2]]['Gama'].append(fp(r5[k], 'Gama'))
        S[k[:2]][k[2]]['RA6'].append(fp(r6[k], 'RA6'))
        S[k[:2]][k[2]]['fp64'].append(fp(r10[k], 'RA6-fp64'))
    L += ['## 二、按设置的尾段误报总量（不含探测重放；种子均值后对负载求和）', '',
          '| 设置 | 负载 | Gama | RA6（带索引） | **RA6-fp64** | RA6-fp64 / RA6 | RA6-fp64 / Gama | 不差于 Gama |',
          '|---|---:|---:|---:|---:|---:|---:|---|']
    crit = dict(n=0, gama=0)
    for ds, kib in sorted(S, key=lambda x: (ORDER.index(x[0]), x[1])):
        ws = S[ds, kib]
        t = {m: sum(np.mean(ws[w][m]) for w in ws) for m in ('Gama', 'RA6', 'fp64')}
        ok = t['fp64'] <= 1.01 * t['Gama']
        crit['n'] += 1
        crit['gama'] += ok
        star = ' ★' if HIGH.get(ds) == kib else ''
        L.append(f"| {ds} {kib}{star} | {len(ws)} | {t['Gama']:,.0f} | {t['RA6']:,.0f} | **{t['fp64']:,.0f}** | "
                 f"{ratio(t['fp64'], t['RA6']):.3f} | {ratio(t['fp64'], t['Gama']):.3f} | {'是' if ok else '否'} |")
    L += ['', f"按总量不比 Gama 差超过 1%：{crit['gama']}/{crit['n']} 个设置。", '']

    pk = [k for k in keys if k[2] == PROBE]
    pr = [ratio(fp(r10[k], 'RA6-fp64'), fp(r6[k], 'RA6')) for k in pk]
    pg = [ratio(fp(r10[k], 'RA6-fp64'), fp(r5[k], 'Gama')) for k in pk]
    L += ['## 三、探测重放（稳健性，单列）', '',
          f'{len(pk)} 个案例：RA6-fp64 / RA6 {cell(pr)}；RA6-fp64 / Gama {cell(pg)}（中位数 / 最坏 / ≤1 的比例）。', '']

    rows = [r10[k]['RA6-fp64'] for k in keys]
    fn = sum(int(r['member_hits_final']) for r in rows)
    bound = max(float(r['fn_bound_per_query']) for r in rows)
    cached = [r for r in rows if int(r['cache_alloc_bytes']) > 0]
    frac_same = np.mean([r10[k]['RA6-fp64']['trees'] == r6[k]['RA6']['trees'] and
                         (int(r10[k]['RA6-fp64']['cache_alloc_bytes']) > 0) == (int(r6[k]['RA6']['cache_alloc_bytes']) > 0)
                         for k in keys])
    L += ['## 四、假阴性和代价', '',
          f'- 全部 {len(keys)} 个案例的最终缓存状态上，用全部成员逐个查询，被缓存误判为负例的成员数合计：**{fn}**。',
          f'- 理论上界：每次成员查询的假阴性概率 ≤ 已占用槽位数 × 2^-64，所有案例中最大为 {bound:.2e}。',
          f'- {len(cached)}/{len(keys)} 个案例用了缓存。',
          f'- 与第六轮选出的树数相同、且是否用缓存相同的案例：{frac_same:.0%}。',
          '- 不再需要成员哈希索引：省掉每个成员 8 字节的预算外内存，缓存插入也不再需要查索引。', '']
    L += decompose_section(r10, keys)
    (ROOT / 'results' / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

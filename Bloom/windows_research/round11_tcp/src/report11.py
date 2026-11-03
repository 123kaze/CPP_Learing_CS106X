"""Round-11 report: protocol-consistent (TCP-only) real traces -> results/report.md

Rules fixed in plan/design-freeze.md (same as round 6's E1): per setting, tail FPs of every method on
the one real-trace stream; pass = RA6 total not worse than Gama by more than 1%; ratios (fp+1)/(fp+1).
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = {'nomodel': 'nomodel', 'run5': 'run5/results', 'run6': 'run6/results/main', 'run10': 'run10/results/main', 'grid10': 'grid10/results/grid'}
NAMES = {'caida_tcp_flow': 'Caida', 'mawi2020_tcp_flow': 'MAWI 2020', 'mawi2021_tcp_flow': 'MAWI 2021',
         'mawi2022_tcp_flow': 'MAWI 2022'}


def ratio(a, b):
    return (a + 1) / (b + 1)


def load():
    out = defaultdict(dict)
    for d in DIRS.values():
        for f in sorted((ROOT / 'results' / d).glob('rows_*.csv')):
            for r in csv.DictReader(open(f, encoding='utf-8')):
                out[r['dataset'], int(r['budget_kib'])][r['method']] = r
    return out


def main():
    meta = json.loads((ROOT / 'results' / 'datasets.json').read_text())
    R = load()
    L = ['# 第十一轮：协议一致（只用 TCP）的真实轨迹', '',
         '设计见 `plan/design-freeze.md`（写于看到结果之前）：只保留 TCP 包；前一半时间里出现过的流是成员，之后才出现的流是负例；'
         '查询是后一半的 TCP 包。key 不含协议，模型只用 src、dst。每条轨迹 1 条真实查询流，前 25% 为学习期，只统计后 75%。', '',
         '## 数据', '',
         '| 轨迹 | TCP 包 | 成员流 | 负例流 | 评估段落在负例上的包 | 与成员 key 完全相同的负例 | 模型输入与某个成员相同的负例 | 预算 KiB（1/2/4/12 位每成员） |',
         '|---|---:|---:|---:|---:|---:|---:|---|']
    for ds, m in meta.items():
        L.append(f"| {NAMES[ds]} | {m['tcp_packets']:,} | {m['members']:,} | {m['negatives']:,} | {m['tail_packets_on_negatives']:,} | "
                 f"{m['negatives_sharing_exact_key_with_member']} | {m['negatives_sharing_model_input_with_member'] / m['negatives']:.0%} | "
                 f"{' / '.join(map(str, m['budgets_kib']))} |")
    L += ['', '"模型输入相同"按 float32 地址（IPv4 约等于 /24 前缀）计：这部分负例与某个成员流在模型看来完全一样，学习型过滤器无法靠模型分开它们。', '',
          '## 评估段误报数', '',
          '| 轨迹 | 预算 KiB | 位/成员 | Gama | Gama+10% | 网格 | 事后最优 | RA4 | **RA6** | RA6-fp64 | 网格-fp64 | RA6/Gama | RA6/网格 | RA6/最优 | RA6-fp64/网格-fp64 | 不差于 Gama |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    npass = ntot = 0
    for ds in meta:
        for i, kib in enumerate(meta[ds]['budgets_kib']):
            r = R.get((ds, kib), {})
            need = ('Gama', 'LearnGrid', 'RA4', 'RA6', 'RA6-fp64', 'LearnGrid-fp64')
            if not all(k in r for k in need):
                L.append(f'| {NAMES[ds]} | {kib} | {(1, 2, 4, 12)[i]} | 未完成 |')
                continue
            f = {k: int(r[k]['fp_tail']) for k in need}
            g10 = int(r['Gama+10%']['fp_tail']) if 'Gama+10%' in r else None
            orc = r['RA4']['fp_oracle']
            orc = int(float(orc)) if orc != '' else None
            ok = f['RA6'] <= 1.01 * f['Gama']
            npass += ok
            ntot += 1
            star = ' ★' if i == 3 else ''
            L.append(f"| {NAMES[ds]} | {kib}{star} | {(1, 2, 4, 12)[i]} | {f['Gama']:,} | {g10 if g10 is None else f'{g10:,}'} | "
                     f"{f['LearnGrid']:,} | {'—' if orc is None else f'{orc:,}'} | {f['RA4']:,} | **{f['RA6']:,}** | "
                     f"{f['RA6-fp64']:,} | {f['LearnGrid-fp64']:,} | {ratio(f['RA6'], f['Gama']):.3f} | "
                     f"{ratio(f['RA6'], f['LearnGrid']):.3f} | {'—' if orc is None else f'{ratio(f["RA6"], orc):.3f}'} | "
                     f"{ratio(f['RA6-fp64'], f['LearnGrid-fp64']):.3f} | {'是' if ok else '否'} |")
    L += ['', f'**过关标准（按设置总量不比 Gama 差超过 1%）：{npass}/{ntot}。**', '',
          '## 不用模型的对照：纯 BF 和 BF + 缓存（`src/nomodel11.py`）', '',
          'Gama 和 RA6 的候选最少也有 1 棵树。这里补上 t = 0：整个预算给一个 BF（最优 k），'
          'BF + 缓存则从同一组缓存比例里用学习期回放来选（与网格的做法相同）。', '',
          '| 轨迹 | 预算 KiB | 纯 BF | BF + 缓存 | **RA6** | RA6 / (BF + 缓存) | BF + 缓存-fp64 | RA6-fp64 | RA6-fp64 / (BF + 缓存-fp64) |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    rr, rf = [], []
    for ds in meta:
        for i, kib in enumerate(meta[ds]['budgets_kib']):
            r = R.get((ds, kib), {})
            if not all(k in r for k in ('BF', 'BF+缓存', 'BF+缓存-fp64', 'RA6', 'RA6-fp64')):
                continue
            f = {k: int(r[k]['fp_tail']) for k in ('BF', 'BF+缓存', 'BF+缓存-fp64', 'RA6', 'RA6-fp64')}
            a, b = ratio(f['RA6'], f['BF+缓存']), ratio(f['RA6-fp64'], f['BF+缓存-fp64'])
            rr.append(a)
            rf.append(b)
            L.append(f"| {NAMES[ds]} | {kib}{' ★' if i == 3 else ''} | {f['BF']:,} | {f['BF+缓存']:,} | **{f['RA6']:,}** | {a:.3f} | "
                     f"{f['BF+缓存-fp64']:,} | {f['RA6-fp64']:,} | {b:.3f} |")
    if rr:
        import numpy as np
        L += ['', f'RA6 / (BF + 缓存)：中位 {np.median(rr):.3f}，范围 {min(rr):.3f}–{max(rr):.3f}，≤1 的 {sum(x <= 1 for x in rr)}/{len(rr)}；'
              f'指纹缓存版中位 {np.median(rf):.3f}，≤1 的 {sum(x <= 1 for x in rf)}/{len(rf)}。', '']
    L += ['',
          '评估段长度（查询数）与 FPR：', '']
    for ds in meta:
        for kib in meta[ds]['budgets_kib']:
            r = R.get((ds, kib), {})
            if 'RA6' in r and 'Gama' in r:
                n = int(r['RA6']['fp_tail']) / float(r['RA6']['fpr_tail']) if float(r['RA6']['fpr_tail']) else float('nan')
                L.append(f"- {NAMES[ds]} {kib}KiB：评估段 {n:,.0f} 次查询，Gama FPR {float(r['Gama']['fpr_tail']):.3%}，"
                         f"RA6 FPR {float(r['RA6']['fpr_tail']):.3%}，RA6 选 {r['RA6']['trees']} 棵树、缓存 {int(r['RA6']['cache_alloc_bytes']):,} B")
    (ROOT / 'results' / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

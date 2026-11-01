"""RA6 vs the authors' Gama, using saved results only (no training or selection).

Round-5 Gama(original) rows already replay the original FP flags on our streams.
For the later MAWI 2020/2024 original-code runs, replay their saved flags on the
same tail. Do not modify frozen results. Run from round6_bucket:
  ../../.condaenv/bin/python -u src/report_gama_original.py
"""
import json
from collections import defaultdict
import numpy as np
import report6 as R

ROOT = R.ROOT
ORIGINAL = ROOT.parents[1] / 'original_baselines' / 'gama' / 'out'


def supplement(original, rows, ds):
    """Evaluate saved original FP flags, not a newly selected or trained model."""
    import holdout6  # Registers the holdout in the shared dataset registry.
    import ra6
    E5 = ra6.E5
    setup, _, _ = E5.load(ds)
    stream = E5.base_stream(setup, '真实轨迹', None, 0)
    tail = stream[len(stream) // 4:]
    for k in sorted(rows):
        if k[0] != ds or k in original:
            continue
        meta_file = ORIGINAL / ds / f'gama_{k[1]}.json'
        if not meta_file.exists():
            continue
        meta = json.loads(meta_file.read_text())
        if 'infeasible' in meta:
            continue
        flags = np.load(ORIGINAL / ds / f'fp_{k[1]}.npy')
        assert meta['member_false_negatives'] == 0
        assert len(flags) == len(setup.h1q) == meta['query_pool']
        assert k[2:] == ('真实轨迹', 0)
        fp = int(flags[tail].sum())
        original[k] = dict(fp_tail=fp, fpr_tail=fp / len(tail))


def number(x):
    return f'{x:,.1f}'.removesuffix('.0')


def totals_table(keys, baseline, ra, original):
    groups = defaultdict(list)
    for k in keys:
        groups[k[:2]].append(k)
    lines = ['| 设置（KiB） | 原版 Gama | 同引擎 Gama | RA6（冷启动） | RA6 / 原版 |',
             '|---|---:|---:|---:|---:|']
    counts = dict(better=0, equal=0, worse=0, missing=0)
    for ds, kib in sorted(groups, key=lambda x: ((R.ORDER + ['mawi2024_flow']).index(x[0]), x[1])):
        kk = groups[ds, kib]
        def total(get):
            workloads = defaultdict(list)
            for k in kk:
                workloads[k[2]].append(get(k))
            return sum(float(np.mean(v)) for v in workloads.values())
        a = total(lambda k: R.fp(ra[k], 'RA6'))
        g = total(lambda k: R.fp(baseline[k], 'Gama'))
        if all(k in original for k in kk):
            o = total(lambda k: int(original[k]['fp_tail']))
            counts['better' if a < o else 'worse' if a > o else 'equal'] += 1
            original_text = number(o)
            ratio_text = f'{R.ratio(a, o):.4f}' if o else '—（原版为 0）'
        else:
            counts['missing'] += 1
            p = ORIGINAL / ds / f'gama_{kib}.json'
            meta = json.loads(p.read_text()) if p.exists() else {}
            original_text = '原版运行失败' if 'infeasible' in meta else '未完成/缺结果'
            ratio_text = '—'
        star = ' ★' if R.HIGH.get(ds) == kib or (ds == 'mawi2024_flow' and kib == 128) else ''
        lines.append(f'| {ds} {kib}{star} | {original_text} | {number(g)} | {number(a)} | {ratio_text} |')
    lines += ['', f'可对比 {counts["better"] + counts["equal"] + counts["worse"]} 个设置：'
              f'RA6 误报更少 {counts["better"]} 个，相同 {counts["equal"]} 个，更多 {counts["worse"]} 个；'
              f'缺少可用原版结果 {counts["missing"]} 个。', '']
    return lines


def main():
    r5, r6 = R.load(R.R5), R.load(ROOT / 'results' / 'main')
    original = {k: v['Gama(original)'] for k, v in r5.items() if 'Gama(original)' in v}
    supplement(original, r6, 'mawi2020_flow')
    keys = sorted(k for k in r6 if 'RA6' in r6[k] and k in r5 and k[2] != R.PROBE)
    paired = [k for k in keys if k in original]
    lines = ['# RA6 与作者原版 Gama 的直接对比（2026-11-01）', '',
             '## 1. 数据来源与口径', '',
             '- **RA6**：第六轮 `results/main/rows_*.csv`，不预热缓存，不是 RA6-warm。',
             '- **作者原版 Gama**：`original_baselines/gama/run_gama_plbf_ada.py`，官方提交 `27a454a` 的适配副本；保留原搜索、模型参数、pickle 记账和 FastPLBF_M N=50、k=5。',
             '- 原版在相同查询流上的结果来自第五轮 `results/rows_*.csv` 的 `Gama(original)`；MAWI 2020/2024 使用本次已跑完的原版输出 `original_baselines/gama/out/`，仅回放保存的 FP 标记。',
             '- 同引擎 Gama 单独保留：它采用紧凑数组记账和 DP N=1000，并非作者源代码。不能把两者混称。',
             '- 按（数据集、预算、负载、种子）对齐，前 25% 学习、后 75% 评估。本报告不含探测重放。',
             '- 下表是尾段误报数：先对种子取均值，再对负载求和，不是假阳率百分数。同一案例的查询分母一致，误报数下降也意味着假阳率下降。',
             '- 比值沿用 `(FP_RA6+1)/(FP_Gama原版+1)`；原版为 0 的设置不解释倍数，直接看绝对误报。★ 为高预算点。',
             f'- 主负载共有 {len(keys)} 个 RA6 案例，其中 {len(paired)} 个有可用原版结果。', '',
             '## 2. 主数据集：逐设置误报总量', '']
    lines += totals_table(keys, r5, r6, original)
    lines += ['原版失败的 16KiB 设置不是已测得 FPR=1，也不算 RA6 获胜：原脚本前 5 轮大小样本不足，在线性拟合处报 `TypeError: expected x and y to have same length`。这是该原版实现/搜索流程在此预算下的失败，不是证明所有 Gama 实现都放不下。', '',
              '## 3. 主数据集：逐案例比值', '',
              f'仅计入第五轮参照值（事后最优，否则网格）≥{R.MIN_REF} 的配对案例，保持第六轮主报告口径。不是把所有低误报案例纳入中位数。', '',
              '| 分组 | 计入 | 排除低参照值 | RA6 / 原版（中位数 / 最坏 / ≤1 比例） |',
              '|---|---:|---:|---|']
    grouped = defaultdict(list)
    for k in paired:
        for group in (R.group(k[2]), '合计（不含探测重放）'):
            grouped[group].append(k)
    for group in ('1万', '10万', '100万', '全部', '每key一次/全新对抗', '真实轨迹', '合计（不含探测重放）'):
        kk = grouped[group]
        kept = [k for k in kk if R.ref(r5[k]) >= R.MIN_REF]
        ratios = [R.ratio(R.fp(r6[k], 'RA6'), int(original[k]['fp_tail'])) for k in kept]
        lines.append(f'| {group} | {len(kept)} | {len(kk) - len(kept)} | {R.cell(ratios)} |')
    h5 = R.load(ROOT / 'results' / 'holdout' / 'round5_methods')
    h6 = R.load(ROOT / 'results' / 'holdout')
    supplement(original, h6, 'mawi2024_flow')
    hk = sorted(k for k in h6 if 'RA6' in h6[k] and k in h5)
    lines += ['', '## 4. MAWI 2024：补充原版对照', '',
              '复用已冻结方法的 RA6 结果；原版 Gama 是之后补跑的对照，不声称这次补充比较事先预登记。', '']
    lines += totals_table(hk, h5, h6, original)
    lines += ['## 5. 时间：哪些测了，哪些没有', '',
              '| 指标 | 现有实验/报告 | 能否声称 RA6 对作者原版更快 |',
              '|---|---|---|',
              '| 查询时间 | 第六轮 `results/e789_report.md`，E7 | **不能**：Gama 列是同引擎复现；作者原版查询时间未测 |',
              '| SQLite 端到端时间 | 同一报告，E8 | **不能**：同样不是作者原版 |',
              '| 选择/构建时间 | 第五轮 `results/e4_report.md`，E4 | **不能**：Gama 列是同引擎复现 |',
              '| 原版搜索加构建时间 | `original_baselines/gama/out/<dataset>/gama_<budget>.json` 的 `search_and_build_ms` | 只有原版单独记录，包含训练及查询池打分等阶段，与 E4 不同口径，不能直接算加速比 |', '',
              '此前准备的原版 Gama 单线程三次计时任务启动被工具阻止，未获得该轮结果；本报告未重启该任务，也没有补测查询时间。', '',
              '## 6. 结论边界', '',
              '- 这是**原版实现到 RA6 的整体差异**。其中包含模型参数、搜索、内存表示、分段分配和缓存等变化，不能把全部收益归因于 RA6 的按桶精算。按桶精算的贡献应看 RA6 对 RA4/网格及消融。',
              '- RA6 缓存插入依赖预算外的成员哈希索引；作者原版 Gama 不需要这份索引。等过滤器预算不等于等总系统内存，见 `results/e789_report.md` 的系统假设。',
              '- 不能写“所有设置胜出”，也不能根据误报更少推断查询或构建一定更快。', '',
              '复现：在 `windows_research/round6_bucket/` 运行 `../../.condaenv/bin/python -u src/report_gama_original.py`。此脚本只汇总/回放已有输出，不训练模型、不重新选择 RA6、不修改冻结实验。', '']
    dest = ROOT / 'results' / 'ra6_vs_gama_original.md'
    dest.write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()

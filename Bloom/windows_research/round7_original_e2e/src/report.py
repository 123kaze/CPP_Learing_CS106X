"""Report measured native paths, keeping original code separate from our Gama replica."""
import shared as S
import argparse
import json
from collections import defaultdict
import numpy as np


def main(suffix):
    dest = S.ROOT / 'results' / suffix
    groups = defaultdict(lambda: defaultdict(list))
    failures = []
    for f in sorted(dest.glob('*_rep*_*.json')):
        row = json.loads(f.read_text())
        if row['status'] != 'ok':
            failures.append((f.name, row.get('error', row.get('original_error', row['status']))))
            continue
        groups[row['dataset'], row['budget_kib']][row['method']].append(row)
    def med(rows, get):
        return float(np.median([get(r) for r in rows]))
    lines = ['# 作者原版 Gama vs RA6：真实训练、构建和查询', '',
             '配置见本实验目录 README。每次独立进程重新训练/选择/构建，单线程；查询真实执行模型和过滤器。'
             '下表均为重复中位数，括号里的重复次数必须读：不足 3 次时是阶段结果。', '',
             '**重要：** 原版是官方 Python/LightGBM/bloom_filter 路径；RA6 是冻结的 Numba 紧凑数组路径。'
             '速度差包含实现差异。没有计入数据库或网络后端延迟。', '',
             '## 1. 全负例尾段：FPR 与实际查询时间（batch=1000，冷缓存）', '',
             '| 设置 KiB | 重复 原版/RA6 | 尾段负查询 | 原版 FP / FPR | RA6 FP / FPR | 原版查询秒 | RA6查询秒 | 原版/RA6时间 |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    pairs = []
    for setting in sorted(groups, key=lambda x: (list(S.SETTINGS).index(x[0]), x[1])):
        g = groups[setting]
        if not all(m in g for m in ('Gama(original)', 'RA6')):
            continue
        orig, ra = g['Gama(original)'], g['RA6']
        pairs.append((setting, orig, ra))
        q = lambda r: r['queries']['negative_tail']
        assert len({q(r)['queries'] for r in orig + ra}) == 1
        n = q(orig[0])['queries']
        of, rf = med(orig, lambda r: q(r)['fp']), med(ra, lambda r: q(r)['fp'])
        ot, rt = med(orig, lambda r: q(r)['seconds']), med(ra, lambda r: q(r)['seconds'])
        lines.append(f'| {setting[0]} {setting[1]} | {len(orig)}/{len(ra)} | {n:,} | {of:,.0f} / {of/n:.6%} | '
                     f'{rf:,.0f} / {rf/n:.6%} | {ot:.3f} | {rt:.3f} | {ot/rt:.2f}× |')
    lines += ['', '## 2. 从头构建与完成整个尾段的时间（秒）', '',
              '构建 = 从内存中的训练数据到可执行过滤器。原版训练/搜索交织；RA6 计入 200 树训练、所有候选打分、'
              '学习统计、前 5 候选构建/精算、模型数组与最终 BF、成员索引构建。总计算时间 = 构建 + 全负例尾段查询。', '',
              '| 设置 | 原版构建 | RA6训练 | RA6打分/准备 | RA6选择/构建 | RA6可执行结构/索引 | RA6构建合计 | 原版总计算 | RA6总计算 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for (ds, kib), orig, ra in pairs:
        values = [med(orig, lambda r: r['train_to_ready_s'])]
        values += [med(ra, lambda r: r[k]) for k in ('train_s', 'score_prepare_s', 'select_build_s',
                                                   'executable_prepare_s', 'train_to_ready_s')]
        values += [med(rows, lambda r: r['train_plus_tail_s']) for rows in (orig, ra)]
        lines.append(f'| {ds} {kib} | ' + ' | '.join(f'{v:.3f}' for v in values) + ' |')
    lines += ['', '## 3. 10% 成员混入：单条与批量 API（ns/query）', '',
              '同一尾段的前 20 万条混合查询用于 batch=1000；其前 2 万条用于 batch=1。两者都从空缓存开始，'
              '不是全尾段延迟；单条 API 包含 Python 调用开销。', '',
              '| 设置 | 原版 batch=1 | RA6 batch=1 | 原版 batch=1000 | RA6 batch=1000 |',
              '|---|---:|---:|---:|---:|']
    for (ds, kib), orig, ra in pairs:
        values = [med(rows, lambda r: r['queries'][kind]['ns_per_query'])
                  for kind in ('mixed_scalar', 'mixed_batch') for rows in (orig, ra)]
        lines.append(f'| {ds} {kib} | ' + ' | '.join(f'{v:,.0f}' for v in values) + ' |')
    lines += ['', '## 4. 预算与正确性', '',
              '同一个预算参数不是同样的物理内存：原版仍按 pickle + 目标 BF 位数选择；实际 BF 后端数组可能更大。'
              '下面 pickle 只是原版预算指标，不是进程 RSS 或真实模型内存。', '',
              '| 设置 | 原版树数 | RA6树数 | 原版模型pickle B | 原版BF目标 B | 原版BF数组payload B | RA6过滤器 B | RA6预算外索引 B |',
              '|---|---|---|---:|---:|---:|---:|---:|']
    for (ds, kib), orig, ra in pairs:
        trees = lambda rows: ','.join(str(t) for t in sorted({r['trees'] for r in rows}))
        values = [med(orig, lambda r: r['model_pickle_bytes']), med(orig, lambda r: r['bf_target_bits']/8),
                  med(orig, lambda r: r['bf_array_payload_bytes']), med(ra, lambda r: r['used_bytes']),
                  med(ra, lambda r: r['member_index_bytes'])]
        lines.append(f'| {ds} {kib} | {trees(orig)} | {trees(ra)} | ' + ' | '.join(f'{v:,.0f}' for v in values) + ' |')
    all_rows = [r for _, orig, ra in pairs for r in orig + ra]
    assert all(r['member_false_negatives'] == 0 for r in all_rows)
    assert all(r['main_table_check']['equal'] for _, _, ra in pairs for r in ra)
    lines += ['', f'- 已配对成功的 {len(all_rows)} 次构建，全部成员检查零假阴性；混合查询同样零假阴性。',
              '- RA6 的全尾段 FP、树数、缓存字节均通过冻结主表回归。',
              '- 逐次耗时、load average、软件版本、源码 SHA256、计时批次分位数、原版与既有结果的差异见逐次 JSON；日志保留失败堆栈。', '',
              '## 5. 不包含在主表构建/查询时间中的准备与校验（秒）', '',
              '| 设置 | 方法 | 数据读取/准备 | 查询输入排列 | JIT预热 | 校验 | 进程墙钟 |',
              '|---|---|---:|---:|---:|---:|---:|']
    for (ds, kib), orig, ra in pairs:
        for method, rows in (('原版', orig), ('RA6', ra)):
            values = [med(rows, lambda r: r.get(k, 0)) for k in
                      ('read_prepare_s', 'query_input_prepare_s', 'jit_setup_s', 'verification_s', 'process_wall_s')]
            lines.append(f'| {ds} {kib} | {method} | ' + ' | '.join(f'{v:.3f}' for v in values) + ' |')
    lines += ['', '## 失败记录', '']
    lines += [f'- `{name}`：`{error.strip().splitlines()[-1]}`' for name, error in failures] or ['无已记录的失败。']
    (dest / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'REPORT {len(pairs)} paired settings; {len(failures)} errors: {dest / "report.md"}', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--suffix', default='main')
    main(p.parse_args().suffix)

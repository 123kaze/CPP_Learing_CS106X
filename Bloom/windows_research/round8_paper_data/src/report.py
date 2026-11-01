"""Keep public-source reconstruction distinct from numeric reproduction of paper tables."""
import paper_common as P
import json
from collections import defaultdict
import numpy as np


def main():
    dest = P.ROOT / 'results'
    groups = defaultdict(lambda: defaultdict(list))
    errors = []
    for f in sorted(dest.glob('*_rep*.json')):
        r = json.loads(f.read_text())
        if r['status'] != 'ok':
            errors.append((f.name, r.get('error', r['status']).splitlines()[-1]))
            continue
        groups[r['dataset'], r['budget_kib']][r['method']].append(r)
    lines = ['# Gama 论文公开原始数据源：作者方法与 RA6 重评估', '',
             '**不是论文精确数值复现。** 作者最终 CSV、划分和 Yelp embedding 不公开；URL 使用公开作者特征，'
             'COD 使用论文链接同一原始源。原样方法参数和测量口径见 README。查询秒是本机实际运行实现的时间，'
             '不等同论文服务器时间，更不是纯算法速度消融。', '', '## 数据审计', '']
    for ds in ('paper_url', 'paper_cod'):
        f = P.ROOT / 'data' / ds / 'audit.json'
        if f.exists():
            audit = json.loads(f.read_text())
            P.S.save(dest / f'{ds}_data_audit.json', audit)
            lines.append(f'- {ds}：成员 {audit["members"]:,}，负例 {audit["negatives"]:,}；'
                         f'论文 {audit["paper_members"]:,} / {audit["paper_negatives"]:,}；'
                         f'特征 {len(audit["features"])} 维；精确划分未获得。')
    lines += ['- Yelp：作者过滤后的 CSV、负例生成和完整 embedding 未取得，不伪造替代数据。', '',
              '## 静态全测试负例池：每个 key 查一次，冷缓存', '',
              '| 数据/预算KiB | 方法 | 成功重复 | FP中位数 | FPR中位数 | 构建秒 | 全池查询秒 |',
              '|---|---|---:|---:|---:|---:|---:|']
    med = lambda rows, get: float(np.median([get(r) for r in rows]))
    for (ds, kib), methods in sorted(groups.items()):
        for method, rows in sorted(methods.items()):
            q = lambda r: r['workloads']['once']['pool'] if method == 'RA6' else r['pool']
            build = lambda r: r['workloads']['once']['train_to_ready_s'] if method == 'RA6' else r['train_to_ready_s']
            lines.append(f'| {ds} {kib} | {method} | {len(rows)} | {med(rows,lambda r:q(r)["fp"]):,.0f} | '
                         f'{med(rows,lambda r:q(r)["fpr"]):.6%} | {med(rows,build):.3f} | {med(rows,lambda r:q(r)["seconds"]):.3f} |')
    lines += ['', '## 相同学习期与评估尾段（前25%/后75%）', '',
              '| 数据/预算KiB | 方法 | 负载 | 成功重复 | 尾段FP | 尾段FPR | 查询秒 | ns/query |',
              '|---|---|---|---:|---:|---:|---:|---:|']
    for (ds, kib), methods in sorted(groups.items()):
        for method, rows in sorted(methods.items()):
            for workload in ('once', 'zipf'):
                q = lambda r: r['workloads'][workload]
                lines.append(f'| {ds} {kib} | {method} | {workload} | {len(rows)} | {med(rows,lambda r:q(r)["fp"]):,.0f} | '
                             f'{med(rows,lambda r:q(r)["fpr"]):.6%} | {med(rows,lambda r:q(r)["seconds"]):.3f} | '
                             f'{med(rows,lambda r:q(r)["ns_per_query"]):,.0f} |')
    lines += ['', '## 预算与正确性', '',
              '原版模型按 pickle 计大小而非 RSS，PLBF 后端可能超目标，RA6 索引预算外。预算参数相同不能写成等物理/系统内存。', '',
              '| 数据/预算KiB | 方法 | 原版pickle/BF目标/BF实际payload B | RA6实际过滤器B（once/zipf） | 预算外索引B |',
              '|---|---|---|---|---:|']
    for (ds, kib), methods in sorted(groups.items()):
        for method, rows in sorted(methods.items()):
            assert all(r['member_false_negatives'] == 0 for r in rows)
            if method == 'RA6':
                used = '/'.join(f'{med(rows,lambda r:r["workloads"][w]["used_bytes"]):,.0f}' for w in ('once','zipf'))
                orig = '—'
            else:
                used = '—'
                orig = f'{med(rows,lambda r:r["model_pickle_bytes"]):,.0f}/{med(rows,lambda r:r["bf_target_bits"]/8):,.0f}/{med(rows,lambda r:r["bf_array_payload_bytes"]):,.0f}'
            lines.append(f'| {ds} {kib} | {method} | {orig} | {used} | {med(rows,lambda r:r["member_index_bytes"]):,.0f} |')
    lines += ['', '## 与论文表2的 G-LBF 数字：不直接计算“复现误差”', '',
              '论文 URL G-LBF：64/128/192（表头196）/256/320KB 对应 5.471/0.974/0.170/0.060/0.039%。'
              '由于最终数据、划分、依赖和硬件不一致，上表只能用于条件明确的重评估。论文 G-PLBF 对照是图7的192KB，不是表2。', '',
              '## 失败/未完成', '']
    lines += [f'- `{name}`：{error}' for name,error in errors] or ['尚无已记录错误；完整性请看每行成功重复次数，不能把阶段结果当3次完成。']
    (dest / 'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'REPORT {len(groups)} settings, {len(errors)} failures', flush=True)


if __name__ == '__main__':
    main()

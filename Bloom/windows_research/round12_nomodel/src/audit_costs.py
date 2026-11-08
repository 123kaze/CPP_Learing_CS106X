"""Recompute construction breakdowns from round-8 JSON; no new timing experiment."""
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'round8_paper_data/results'


def sec(value):
    value = float(value)
    assert math.isfinite(value) and value >= 0
    return value


def main():
    rows, source_hashes = [], {}
    for ds in ('paper_url', 'paper_cod'):
        for kib in (64, 128, 192, 256, 320):
            for code in ('LBF', 'PLBF', 'RA6'):
                for rep in range(3):
                    p = SOURCE / f'{ds}_{kib}_{code}_rep{rep}.json'
                    raw = p.read_bytes()
                    source_hashes[p.name] = hashlib.sha256(raw).hexdigest()
                    d = json.loads(raw)
                    assert d['status'] == 'ok' and d['member_false_negatives'] == 0
                    for w in ('once', 'zipf'):
                        r = dict(dataset=ds, budget_kib=kib, method=code, rep=rep, workload=w,
                                 read_prepare_s=sec(d['read_prepare_s']),
                                 jit_setup_s=d.get('jit_setup_s'), query_input_prepare_s=d.get('query_input_prepare_s'),
                                 process_wall_s=sec(d['process_wall_s']))
                        if code == 'RA6':
                            q = d['workloads'][w]
                            common = sec(d['common_train_prepare_s'])
                            train = sec(d['train_s'])
                            score = sec(d['score_and_input_prepare_s'])
                            select = sec(q['select_executable_s'])
                            total = sec(q['train_to_ready_s'])
                            assert abs(total - common - select) < 1e-6
                            assert abs(common - train - score) < .01
                            assert w != 'once' or q['cache_bytes'] == 0
                            r.update(train_s=train, score_input_prepare_s=score, select_executable_s=select,
                                     timer_residual_s=common-train-score, train_to_ready_s=total,
                                     search_train_score_s=None, final_score_and_insert_s=None,
                                     trees=q['trees'], cache_bytes=q['cache_bytes'])
                        else:
                            total = sec(d['train_to_ready_s'])
                            final = sec(d['final_bf_build_s']) if code == 'PLBF' else None
                            r.update(train_s=None, score_input_prepare_s=None, select_executable_s=None,
                                     timer_residual_s=None, train_to_ready_s=total,
                                     search_train_score_s=(total-final) if final is not None else None,
                                     final_score_and_insert_s=final, trees=d['trees'], cache_bytes=0)
                            assert final is None or total >= final
                        rows.append(r)
    out = ROOT / 'results'
    out.mkdir(parents=True, exist_ok=True)
    with (out/'construction_rows.csv').open('w', encoding='utf-8', newline='') as fh:
        writer=csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    lines = ['# 第八轮完整构建成本核验（复用原始计时，不重新计时）', '',
             '每项是 3 次独立构建的中位数。一次训练服务 once/Zipf 两种结构，公共训练准备成本分别计入各自 train-to-ready，不能将两者相加。', '',
             '| 数据 | KiB | 负载 | 原版 G-LBF | 原版 G-PLBF | RA6 train-to-ready | RA6 训练 | RA6 打分/输入准备 | RA6 选择/可执行结构构建 | RA6/G-PLBF |',
             '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    for ds in ('paper_url', 'paper_cod'):
        for kib in (64, 128, 192, 256, 320):
            for w in ('once', 'zipf'):
                by = {code:[r for r in rows if (r['dataset'],r['budget_kib'],r['workload'],r['method'])==(ds,kib,w,code)]
                      for code in ('LBF','PLBF','RA6')}
                totals={code:median(r['train_to_ready_s'] for r in rs) for code,rs in by.items()}
                components={k:median(r[k] for r in by['RA6']) for k in ('train_s','score_input_prepare_s','select_executable_s')}
                ratio=totals['RA6']/totals['PLBF']
                summary.append(dict(dataset=ds,budget_kib=kib,workload=w,median_totals_s=totals,
                                    ra6_median_components_s=components,ratio_of_median_totals=ratio))
                lines.append(f"| {ds} | {kib} | {w} | {totals['LBF']:.2f} | {totals['PLBF']:.2f} | {totals['RA6']:.2f} | "
                             f"{components['train_s']:.2f} | {components['score_input_prepare_s']:.2f} | "
                             f"{components['select_executable_s']:.2f} | {ratio:.2f} |")
    lines += ['', '## 测量边界（必须保留）', '',
              '- `train_to_ready_s` 从训练开始计起，不包含 RA6 的 JIT 预热和数据读取；并非冷启动整个进程耗时。',
              '- RA6 的 `score_and_input_prepare_s` 混合了不同树数打分、模型数组提取、查询空间整理、成员哈希排序等，不能全部叫“预测打分”。',
              '- `select_executable_s` 包括学习统计、选择、前五个候选构建、可执行结构构造，无法从现有记录独立拆出“纯选择”和“最终 BF 构建”。',
              '- G-PLBF 的 `final_bf_build_s` 还包括正例模型打分，不是纯 BF 插入时间。其余训练、搜索、打分只有合计，没有细粒度计时；G-LBF 仅有总计。',
              '- 各阶段中位数之和通常不等于总时间中位数；请勿拿相加的柱高替代存档的总时间。',
              '- `process_wall_s` 包含验证和长查询测试，不可当作构建成本。原版的查询输入准备在 train-to-ready 之后，RA6 相应准备部分在之前，两者也不是完全相同的管线边界。',
              '- 速度差还包含实现、依赖、记账和搜索空间差异；共享环境下的选择加速不能外推成完整构建加速。',
              '- once 的 RA6 没有缓存，FPR 改善不能归因于重复感知。这里只核验成本，不把结果当作新的算法消融。']
    (out/'construction_cost.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'construction_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'construction_sources.json').write_text(json.dumps(source_hashes,indent=2)+'\n')
    print('Construction audit complete: 90 source runs, 180 workload records, 20 summaries.')


if __name__ == '__main__':
    main()

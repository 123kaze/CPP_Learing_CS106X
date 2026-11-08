"""Report exact equivalence and paired construction timing; old Gama is historical only."""
import csv
import json
from pathlib import Path
from statistics import median
from check_scoring import check

ROOT=Path(__file__).resolve().parents[1]


def main():
    src=ROOT/'results/scoring'
    done=json.loads((src/'completion.json').read_text())
    assert done['fresh_builds']==60 and done['verified_pairs']==30
    raw=[];tables=[]
    lines=['# pred_leaf 工程优化：成对等价性与完整构建时间', '',
           '每个数据/预算各 3 组独立成对重建；新旧方式交替顺序、串行执行。pilot 不参与统计。'
           '每对检查模型、14 个完整分数数组、once/Zipf 配置、BF 位图和原生误报完全一致。', '',
           '| 数据 | KiB | 负载 | 原循环 ready 秒 | pred_leaf ready 秒 | 配对加速中位 | 原打分/准备秒 | 新打分/准备秒 |',
           '|---|---:|---|---:|---:|---:|---:|---:|']
    for ds in ('paper_url','paper_cod'):
        for kib in (64,128,192,256,320):
            pairs=[]
            for rep in range(3):
                pair={mode:json.loads((src/f'{ds}_{kib}_{mode}_rep{rep}.json').read_text()) for mode in ('loop','leaf')}
                checked=check(pair['loop'],pair['leaf']);pairs.append(pair)
                for mode,r in pair.items():
                    for workload in ('once','zipf'):
                        q=r['workloads'][workload]
                        raw.append(dict(dataset=ds,budget_kib=kib,rep=rep,mode=mode,workload=workload,
                                        train_s=r['train_s'],score_and_input_prepare_s=r['score_and_input_prepare_s'],
                                        select_executable_s=q['select_executable_s'],train_to_ready_s=q['train_to_ready_s'],
                                        process_wall_s=r['process_wall_s'],peak_rss_bytes=r['peak_rss_bytes'],
                                        trees=q['trees'],cache_bytes=q['cache_bytes'],fp=q['fp']))
            historical=[json.loads((ROOT.parent/'round8_paper_data/results'/f'{ds}_{kib}_PLBF_rep{rep}.json').read_text()) for rep in range(3)]
            for workload in ('once','zipf'):
                old=[p['loop']['workloads'][workload]['train_to_ready_s'] for p in pairs]
                new=[p['leaf']['workloads'][workload]['train_to_ready_s'] for p in pairs]
                speed=[a/b for a,b in zip(old,new)]
                oldscore=[p['loop']['score_and_input_prepare_s'] for p in pairs]
                newscore=[p['leaf']['score_and_input_prepare_s'] for p in pairs]
                table=dict(dataset=ds,budget_kib=kib,workload=workload,loop_median_ready_s=median(old),
                           leaf_median_ready_s=median(new),median_paired_speedup=median(speed),
                           paired_speedup_range=[min(speed),max(speed)],loop_median_score_prepare_s=median(oldscore),
                           leaf_median_score_prepare_s=median(newscore),
                           historical_original_gplbf_median_s=median(r['train_to_ready_s'] for r in historical))
                tables.append(table)
                lines.append(f"| {ds} | {kib} | {workload} | {median(old):.3f} | {median(new):.3f} | {median(speed):.2f}x | "
                             f"{median(oldscore):.3f} | {median(newscore):.3f} |")
    with (ROOT/'results/scoring_rows.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)
    assert len(raw)==120
    lines += ['', '## 如何解释', '',
              '- 上表 ready 是每个工作负载的公共训练/准备成本加上选择和可执行结构构建。并不包含原始数据读取、JIT 预热、摘要校验或评估查询。',
              '- 配对加速中位是每个重复的新旧 ready 比值再取中位，不是各阶段中位数相加或把旧历史运行与新运行混合。',
              '- 分块叶子矩阵最多 32768×200；没有物化全数据集叶子矩阵。输出的 14 组分数仍是构建工作区，不计入部署结构。峰值 RSS 在逐行表中保留。',
              '- 打分/输入准备字段仍混合模型数组导出、打分、输入整理和成员哈希排序，不把它叫成纯树遍历耗时。',
              '- 旧原版 G-PLBF 总时长只保留在 JSON 中作历史参照；本轮没有重跑它，也没有消除跨实现记账差异，不能据此宣称已公平击败原版。',
              '- 这是实现优化，不改变 RA6 选择规则，不是新方法或新独立验证。若某个预算提速不明显，也必须原样保留。']
    (ROOT/'results/scoring_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (ROOT/'results/scoring_summary.json').write_text(json.dumps(tables,indent=2)+'\n')
    print('Scoring report complete: 60 fresh builds, 30 exact pairs, 120 workload records.')


if __name__=='__main__':main()

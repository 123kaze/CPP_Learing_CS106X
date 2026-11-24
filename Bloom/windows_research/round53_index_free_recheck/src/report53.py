import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
import csv


def non_timing(value):
    if isinstance(value,dict):return {k:non_timing(v) for k,v in value.items() if not k.endswith(('_s','_seconds')) and k not in ('peak_rss_bytes','pilot')}
    if isinstance(value,list):return [non_timing(v) for v in value]
    return value


def compare_pilot(ds,kib):
    a=json.loads((ROOT/f'results/pilot_{ds}_{kib}.json').read_text());b=json.loads((ROOT/f'results/{ds}_{kib}.json').read_text())
    assert non_timing(a)==non_timing(b),f'pilot mismatch {ds}/{kib}'


def stats(pairs):
    ratio=[(a['fp']+1)/(b['fp']+1) for a,b in pairs]
    worst=max(zip(ratio,pairs),key=lambda v:v[0])
    a,b=worst[1]
    return dict(cases=len(pairs),wins=sum(a['fp']<b['fp'] for a,b in pairs),ties=sum(a['fp']==b['fp'] for a,b in pairs),losses=sum(a['fp']>b['fp'] for a,b in pairs),median_paired_smoothed_FP_ratio=float(np.median(ratio)),RA_FP_sum=sum(a['fp'] for a,b in pairs),baseline_FP_sum=sum(b['fp'] for a,b in pairs),worst=dict(dataset=a['dataset'],budget_kib=a['budget_kib'],workload=a['workload'],RA_FP=a['fp'],baseline_FP=b['fp'],smoothed_ratio=worst[0]))


def run():
    start=time.perf_counter();check_sources();rows=[];workers=[]
    for ds in DATASETS:
        for kib in BUDGETS[ds]:
            path=ROOT/f'results/{ds}_{kib}.json';w=json.loads(path.read_text())
            assert w['status']=='complete' and w['member_index_built'] is False
            assert w['peak_rss_bytes']<4*1024**3
            workers.append(w);rows+=w['rows']
    expected={(ds,k,name,0,m) for ds in DATASETS for k in BUDGETS[ds] for name,_ in workloads(ds) for m in METHODS}
    key=lambda r:(r['dataset'],r['budget_kib'],r['workload'],r['seed'],r['method'])
    got={key(r):r for r in rows};assert len(rows)==len(got)==434 and set(got)==expected
    for r in rows:
        assert r['required_member_index_bytes']==0 and r['member_BF_FN']==r['final_member_cache_hits']==0
        assert r['total_bytes']<=r['budget_bytes'] and r['total_bytes']==sum(r[n] for n in ('model_bytes','bf_bytes','metadata_bytes','header_bytes','cache_bytes'))
        if r['method']=='Gama':assert r['Gama_old_FP_regression']
    compare_pilot('url',64);compare_pilot('caida_flow',16)
    groups={'all':lambda d:True,'static_generated_queries':lambda d:not d.endswith('_flow'),'original_four_traces':lambda d:d.endswith('_flow') and d!='mawi2024_flow','previously_used_MAWI24':lambda d:d=='mawi2024_flow'}
    summaries={}
    for group,keep in groups.items():
        summaries[group]={}
        for method in METHODS:
            if method=='RA-PLBF-GT19':continue
            pairs=[(r,got[(r['dataset'],r['budget_kib'],r['workload'],r['seed'],method)]) for r in rows if r['method']=='RA-PLBF-GT19' and keep(r['dataset'])]
            summaries[group][method]=stats(pairs)
    cols=sorted(set().union(*(r.keys() for r in rows))-{'selection_info'})
    with (ROOT/'results/main.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows({k:v for k,v in r.items() if k!='selection_info'} for r in rows)
    per_dataset={}
    for ds in DATASETS:
        a=[r for r in rows if r['dataset']==ds and r['method']=='RA-PLBF-GT19']
        per_dataset[ds]={m:stats([(r,got[(ds,r['budget_kib'],r['workload'],r['seed'],m)]) for r in a]) for m in ('Gama','Replay','RA-global','BF+Exact')}
    ratio=[got[(r['dataset'],r['budget_kib'],r['workload'],r['seed'],'Replay')]['selection_build_s']/r['selection_build_s'] for r in rows if r['method']=='RA-PLBF-GT19']
    verification=dict(status='passed',cases=62,rows=434,methods=list(METHODS),all_budget_checks=True,required_member_index_bytes=0,all_member_BF_FN=0,all_final_member_cache_hits=0,pilot_non_timing_reproductions=2,Gama_old_FP_regressions=62,summary=summaries,per_dataset=per_dataset,selection_build_speedup_median=float(np.median(ratio)),selection_timing_note='one run, loaded frozen model/scores, shared tree/JIT preparation separate; not full rebuild or service speedup',report_wall_s=time.perf_counter()-start)
    save(ROOT/'results/verification.json',verification)
    lines=['# 第53轮结果：无成员验证索引的完整key缓存','','完整执行62case × 7方法 = 434行。所有物理预算、BF成员检查、最终cache完整member检查通过；所需成员验证索引0B。两个固定pilot非计时结果复现，Gama无cache旧FP/树数62/62回归通过。','','## 全矩阵（相关配置，不是62个独立真实负载）','','| RA对照 | 胜 / 平 / 负 | 配对平滑FP比中位 | RA FP简单合计 | 对照FP简单合计 |','| --- | --- | ---: | ---: | ---: |']
    for m,s in summaries['all'].items():lines.append(f"| {m} | {s['wins']} / {s['ties']} / {s['losses']} | {s['median_paired_smoothed_FP_ratio']:.6f} | {s['RA_FP_sum']} | {s['baseline_FP_sum']} |")
    lines+=['','配对比逐case计算(FP_RA+1)/(FP_baseline+1)。简单合计跨预算/相关负载，不是单次部署的总FP。所有低FP设置保留。','',f"加载固定模型/分数后的选择＋构建时间，Replay/RA配对中位{verification['selection_build_speedup_median']:.3f}×；单次运行，公共tree准备/JIT另计，不是训练或服务端到端加速。",'','## 分层结果与最坏反例','']
    for group,methods in summaries.items():
        if group=='all':continue
        lines.append(f'### {group}')
        for m in ('Gama','Replay','RA-global','BF+Exact'):
            s=methods[m];v=s['worst']
            lines.append(f"- 对{m}：{s['wins']}/{s['ties']}/{s['losses']}，中位比{s['median_paired_smoothed_FP_ratio']:.6f}；最大平滑比{v['smoothed_ratio']:.6f}（{v['dataset']} / {v['budget_kib']}KiB / {v['workload']}：RA {v['RA_FP']}，对照 {v['baseline_FP']}）。")
        lines.append('')
    lines+=['## 未解决的边界','','- 这是固定62case的新重跑，不是旧1146case全覆盖，也未重新执行旧Table4端到端时间。','- 固定原模型、特征、split和25%/75%冷tail；没有重新训练。MAWI24是已使用数据的后续变体核验，非新holdout。','- 完整原key存于cache slot，hash只选bucket；URL/Shalla超过128bytes不缓存。旧RA预测未专门建模长keybypass。','- 严格zero-FN要求静态同版本成员集、仅确认negative后插入；当前为离线标签参考回放，没有在线SQL、动态成员或自然混合延迟新证据。','- 原UDP/TCP任务语义限制未因此解决；COD/CAIDA/Shalla/URL的uniform/Zipf是生成工作负载。','- rawkey输入、模型/分数输入、learning状态和RSS另列；无额外部署成员索引不等于输入/工作区免费或相同总RSS。','- 旧前缀结果完整保留，论文不改；本轮不自动发布。','','[计划](plan/design-freeze.md) · [全部结果](results/main.csv) · [核验与分数据集统计](results/verification.json)','']
    (ROOT/'README.md').write_text('\n'.join(lines))
    print('REPORT_COMPLETE',len(rows),flush=True)


if __name__=='__main__':run()

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data44 import *
import statistics


def write_csv(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/'results'/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()})


def report():
    check();qual=[json.loads((ROOT/f'results/{c}_qualification.json').read_text()) for c in CLUSTERS];rows=[];inputs=[];sources={}
    for q in qual:
        name=q['cluster'];m=json.loads((ROOT/f'results/{name}_data.json').read_text())
        for d in q['diagnostics']:inputs.append(dict(cluster=name,eligible=q['eligible_for_method_comparison'],members=m['members'],distinct_negative_keys=m['distinct_negative_keys'],GET_queries=m['GET_queries'],GET_time_reversals=m['GET_time_reversals'],**d))
        if not q['eligible_for_method_comparison']:continue
        for seed in SEEDS:
            p=ROOT/f'results/{name}_{seed}.json';w=json.loads(p.read_text());assert w['status']=='complete';sources[str(p.relative_to(ROOT))]=sha(p)
            for r in w['rows']:
                assert r['member_fn']==r['final_member_cache_hits']==0 and r['auxiliary_total_bytes']<=r['budget_kib']*1024 and r['required_extra_index_bytes']==0
                assert r['mixed_backend_calls']==r['fp']+w['tail_mixed_members']
                rows.append(dict(cluster=name,seed=seed,tail_negative_queries=w['tail_negative_queries'],tail_mixed_queries=w['tail_mixed_queries'],tail_mixed_members=w['tail_mixed_members'],**r))
    write_csv('qualification.csv',inputs);write_csv('main.csv',rows)
    groups={}
    for r in rows:groups.setdefault((r['cluster'],r['seed'],r['budget_kib']),{})[r['method']]=r
    comparisons={}
    for name in CLUSTERS:
        cc={k:g for k,g in groups.items() if k[0]==name}
        if not cc:continue
        comparisons[name]={}
        for baseline in ('BF+Exact128','Replay','RA-global','Gama'):
            pairs=[(r['RA6-Exact128']['fp'],r[baseline]['fp']) for r in cc.values()]
            comparisons[name][baseline]=dict(cases=len(pairs),wins=sum(a<b for a,b in pairs),ties=sum(a==b for a,b in pairs),losses=sum(a>b for a,b in pairs),median_smoothed_ratio=statistics.median((a+1)/(b+1) for a,b in pairs))
    summary=dict(status='verified',fixed_candidates=3,eligible_clusters=[q['cluster'] for q in qual if q['eligible_for_method_comparison']],ineligible_clusters={q['cluster']:q['ineligibility_reasons'] for q in qual if not q['eligible_for_method_comparison']},main_rows=len(rows),paired_case_keys=len(groups),comparisons=comparisons,all_member_FN=0,required_extra_index_bytes=0,original_production_NotFound_evidence=False,task='real request traces queried against constructed prefix-only immutable seen-key checkpoints')
    save(ROOT/'results/summary.json',summary);save(ROOT/'results/verification.json',dict(**summary,worker_sha256=sources))
    text=['# Round44：真实请求驱动的检查点目录（不是原KV存在性实验）','','固定Twitter2020Mar前三个cluster，使用first25%GET seen-key不可变目录；后25%GET learning、后50%tail。样本提取/是否完整连续未被公开文档明确，保持记录顺序，不按timestamp重排。源许可CC BY4.0；不输出原始key/client。','','## 资格：不按AUC或方法赢输筛选','','| cluster | GET数 | members | negative keys | 开发AUC16中位 | overlap中位 | eligible |','| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for q in qual:
        m=json.loads((ROOT/f'results/{q["cluster"]}_data.json').read_text());au=[d['development_auc16'] for d in q['diagnostics'] if d['development_auc16'] is not None]
        text.append(f'| {q["cluster"]} | {m["GET_queries"]} | {m["members"]} | {m["distinct_negative_keys"]} | {statistics.median(au) if au else None} | {statistics.median(d["query_feature_overlap_fraction"] for d in q["diagnostics"]):.6f} | {q["eligible_for_method_comparison"]} |')
    text+=['','## 主方法完整结果','','| cluster | RA vs BF 胜/平/负 | 中位平滑比 | RA vs Replay 胜/平/负 | 中位平滑比 |','| --- | --- | ---: | --- | ---: |']
    for name,r in comparisons.items():
        b=r['BF+Exact128'];p=r['Replay'];text.append(f'| {name} | {b["wins"]}/{b["ties"]}/{b["losses"]} | {b["median_smoothed_ratio"]:.6f} | {p["wins"]}/{p["ties"]}/{p["losses"]} | {p["median_smoothed_ratio"]:.6f} |')
    text+=['','## 每个预算全方法（3seed各自FP中位数，不是配对比）','','| cluster | KiB | Gama | Replay | RA-global | RA | BF+Exact | PlainBF | ZGate |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    methods=('Gama','Replay','RA-global','RA6-Exact128','BF+Exact128','PlainBF','ZGate-Exact128')
    for name in comparisons:
        for kib in sorted({r['budget_kib'] for r in rows if r['cluster']==name}):
            vals=[statistics.median(r['fp'] for r in rows if r['cluster']==name and r['budget_kib']==kib and r['method']==method) for method in methods]
            text.append('| '+name+' | '+str(kib)+' | '+' | '.join(map(str,vals))+' |')
    text+=['','## 边界','', '原日志包含真实cache请求，却没有经核验的原backend Found/NotFound。这里member是检查点前缀seen-key集合：即使原backend真实存在的key，若不在该目录也会是本任务negative。这不是标签造假，因为任务定义公开且精确；但不能把它换名成原生产系统membership或据此宣称Twitter需要RA。','','目录只由前缀构成，没有NASA式全日志未来成功补目录；negative训练/验证key只取learning首次出现者，与query pool互斥。匿名化保留部分结构，不保证原始语义/原key成本完整保留。时间回退/采样未知均披露。','','本轮Exact128保留完整匿名key字节，hash不作cache身份；超长不缓存。模型/BF/cache/routing/header同预算，额外成员索引0。回放包含真实混合顺序、所有member0FN与最终cache检查，但预计算features/flags回放不是SQL端到端延迟。选择/训练/准备/回放分别计时。','','AUC/overlap/重复差只是解释flag，弱诊断不剔除cluster。最终行数由事前规模门限和budget公式决定，重复KiB去重；没有换cluster/降门槛/看tail调生成器。Length支持规则拒绝数在worker中，不能忽略简单规则解释。ZGate学习保证不是未来保证，未隐藏其退化。','','多个seed/预算共用一份sample，不是多个独立生产应用。本轮未改论文、未自动push，最终还需完整成本测试才讨论系统部署收益。','']
    (ROOT/'results/report.md').write_text('\n'.join(text));print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':report()

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker42 import ROOT,W,check,METHODS
import json,csv,statistics,math


def write_csv(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)


def report():
    check();workers=[json.loads((ROOT/f'results/seed{s}.json').read_text()) for s in (3601,3602,3603)]
    assert all(w['status']=='complete' and not w['pilot'] and len(w['timings'])==63 for w in workers)
    rows=[];resource=[];breaks=[]
    for w in workers:
        rows.extend(dict(seed=w['seed'],**r) for r in w['timings'])
        cfg={(r['method'],r['budget_kib']):r for r in w['configurations']}
        for key,c in cfg.items():
            ts=[r for r in w['timings'] if (r['method'],r['budget_kib'])==key];assert len(ts)==3
            assert len({r['fp'] for r in ts})==1 and all(r['member_fn']==0 and r['reference_mask_equal'] and r['reference_cache_equal'] for r in ts)
            resource.append(dict(seed=w['seed'],**c,queries=w['queries'],member_queries=w['member_queries'],fp=ts[0]['fp'],backend_calls=ts[0]['backend_calls'],us_per_query=statistics.median(r['ns_per_query']/1000 for r in ts),query_window_s=statistics.median(r['elapsed_ns']/1e9 for r in ts),strict_static_zero_fn=True,prefix_work_inside_timer=(key[0]=='RA6-prefix'),common_db_file_bytes=w['backend']['file_bytes'],common_db_build_s=w['backend']['build_s']))
        for kib in (8,16,32):
            for baseline in ('BF+Exact128','PlainBF','NoFilter'):
                a=next(r for r in resource if r['seed']==w['seed'] and r['method']=='RA6-Exact128' and r['budget_kib']==kib)
                b=next(r for r in resource if r['seed']==w['seed'] and r['method']==baseline and r['budget_kib']==kib)
                startup=a['train_to_ready_accounted_s']-b['train_to_ready_accounted_s'];saving=b['us_per_query']-a['us_per_query']
                n=math.ceil(max(0,startup)*1e6/saving) if saving>0 else None
                breaks.append(dict(seed=w['seed'],budget_kib=kib,baseline=baseline,extra_accounted_startup_s=startup,saved_query_us=saving,break_even_future_queries=n,status='positive_slope' if saving>0 else 'no_sustained_amortization_at_measured_rates',shared_historical_labels=True,extra_label_lookup_cost_included=False,delta_one_measured_window_s=startup-a['queries']*saving/1e6))
    learning=workers[0]['learning'];assert len(learning)==9 and all(not w['learning'] for w in workers[1:])
    for rep in range(3):
        a=next(r for r in learning if r['rep']==rep and r['arm']=='certified_existing_BF10')
        b=next(r for r in learning if r['rep']==rep and r['arm']=='existing_BF10_no_logging')
        full=next(r for r in learning if r['rep']==rep and r['arm']=='forced_all')
        assert a['backend_calls']==b['backend_calls'] and a['labels_sha256']==b['labels_sha256']==full['labels_sha256']
    write_csv(ROOT/'results/timings.csv',rows);write_csv(ROOT/'results/resources_and_latency.csv',resource);write_csv(ROOT/'results/break_even.csv',breaks);write_csv(ROOT/'results/learning.csv',learning)
    wins={}
    for b in ('BF+Exact128','PlainBF','NoFilter'):
        ratios=[]
        for seed in (3601,3602,3603):
            for kib in (8,16,32):
                aa=[r for r in rows if r['seed']==seed and r['budget_kib']==kib and r['method']=='RA6-Exact128'];bb=[r for r in rows if r['seed']==seed and r['budget_kib']==kib and r['method']==b]
                ratio=statistics.median(next(r for r in aa if r['rep']==rep)['elapsed_ns']/next(r for r in bb if r['rep']==rep)['elapsed_ns'] for rep in range(3));ratios.append(ratio)
        wins[b]=dict(wins=sum(r<1 for r in ratios),ties=sum(r==1 for r in ratios),losses=sum(r>1 for r in ratios),median_paired_ratio=statistics.median(ratios))
    summary=dict(status='verified',query_measurements=len(rows),resource_latency_cases=len(resource),learning_measurements=len(learning),RA6_exact_timing_comparisons=wins,all_member_FN=0,worker_wall_s=sum(w['wall_s'] for w in workers),modern_production_kv=False)
    W.save(ROOT/'results/summary.json',summary);W.save(ROOT/'results/verification.json',dict(**summary,worker_sha256={f'seed{w["seed"]}.json':W.sha(ROOT/f'results/seed{w["seed"]}.json') for w in workers}))
    text=['# Round42：原始key、完整查询路径与SQLite反馈','', '189条查询计时，63个字节/正确性/延迟组合，9条学习采集计时。原始请求顺序、不重采样member比例；每seed的固定前200000条eligible mixed-tail请求。不是独立现代生产KV工作负载。','','## 完整查询延迟','', '| KiB | Method | 三seed us/query中位数 | FP中位数 | 前端/索引字节例(seed3601) |','| --- | --- | ---: | ---: | --- |']
    for kib in (8,16,32):
        for m in METHODS:
            rr=[r for r in resource if r['budget_kib']==kib and r['method']==m];e=next(r for r in rr if r['seed']==3601)
            text.append(f'| {kib} | {m} | {statistics.median(r["us_per_query"] for r in rr):.5f} | {statistics.median(r["fp"] for r in rr)} | {e["filter_bytes"]} / {e["extra_index_bytes"]} |')
    text+=['','上述先每case取3次中位数再按seed汇总；配对方法比值在summary中另算，不能用列中位数相除替代。计时包含raw hash、按需原词法特征、模型、BF/cache、真实SQL、按需safe-prefix搜索与插入；NoFilter不算无用hash/特征。所有方法严格静态zero-FN；prefix需完整同版本索引，exact存完整≤128byte键、超长不缓存。DirectHashIndex拒绝hash不存在，hash相同仍查精确SQL。','','## 学习标签采集（seed3601，16KiB）','', '| Arm | queries | backend calls | seconds median | negative counter bytes |','| --- | ---: | ---: | ---: | ---: |']
    for arm in ('forced_all','certified_existing_BF10','existing_BF10_no_logging'):
        rr=[r for r in learning if r['arm']==arm];e=rr[0];text.append(f'| {arm} | {e["queries"]} | {e["backend_calls"]} | {statistics.median(r["elapsed_ns"]/1e9 for r in rr):.6f} | {e["negative_counter_python_bytes"]} |')
    text+=['','完整入口计数保留被filter拒绝的请求；收集标签逐项等于精确backend真值。同一个现成BF的认证拒绝/精确cache命中可以提供negative标签，额外lookup调用为0；日志计数CPU与内存仍付费。此原型验证采集协议，不是动态更新、并发在线重配置或训练管线已接入生产的证明。强制所有请求查backend作为不同学习协议保留。','','## 构建和回本边界','', 'resources_and_latency.csv列出逐方法训练/特征/score/选择/部署数组重建/索引的accounted startup；共同数据库创建、输入加载、JIT/验证另列，不与query混算。模型训练与候选score仍使用原实验离线pool，pool范围准备成本是该可复现实验的账本，不宣称最优在线实现。break_even.csv只在观测query成本有正收益斜率时给出外推；否则明确无持续回本。此表假设已有共享标签，不能与需要新标签采集的情境混为一谈。','','字节表计数组payload/header与实际索引，不含整个Python解释器、common SQLite/OS page cache或harness持有的全局key列表；后者与RSS单列。临时SQLite DB在退出后清理。数据库不远程、不并发、不加人工等待；大多数查询可能为members，不能用只看negative流的收益解释全部混合延迟。','','不是individual p50/p99；这些是完整窗口wall/N。3次计时及3seed共享同一日志，不作独立样本或显著性声明。全量negative FP看第41轮，本轮短窗口FP不可替代它。','']
    (ROOT/'results/report.md').write_text('\n'.join(text));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':report()

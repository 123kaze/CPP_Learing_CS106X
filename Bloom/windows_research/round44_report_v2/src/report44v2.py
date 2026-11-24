from pathlib import Path
import sys,json,csv,hashlib,statistics,time
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];OLD=ROOT.parent/'round44_trace_snapshot'
CLUSTERS=('cluster001','cluster002','cluster003');SEEDS=(4401,4402,4403)
METHODS=('Gama','Replay','RA-global','RA6-Exact128','BF+Exact128','PlainBF','ZGate-Exact128')


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def merged_diagnostic(cluster,meta,qualification,d):
    if meta['members']!=d['members']:raise ValueError('Parsed/diagnostic member counts disagree')
    return dict(cluster=cluster,eligible=qualification['eligible_for_method_comparison'],distinct_negative_keys=meta['distinct_negative_keys'],GET_queries=meta['GET_queries'],GET_time_reversals=meta['GET_time_reversals'],**d)

def paired(pairs):
    assert pairs
    return dict(cases=len(pairs),wins=sum(a<b for a,b in pairs),ties=sum(a==b for a,b in pairs),losses=sum(a>b for a,b in pairs),median_smoothed_ratio=statistics.median((a+1)/(b+1) for a,b in pairs))

def write_csv(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/'results'/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def save(name,x):
    with (ROOT/'results'/name).open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')

def check():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for p,h in freeze[section].items():assert sha(BLOOM/p)==h,p
    original=json.loads((OLD/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for p,h in original[section].items():assert sha(BLOOM/p)==h,p


def report():
    check();start=time.perf_counter();inputs=[];rows=[];workers=[];metas={};qual={}
    for cluster in CLUSTERS:
        m=json.loads((OLD/f'results/{cluster}_data.json').read_text());q=json.loads((OLD/f'results/{cluster}_qualification.json').read_text());metas[cluster]=m;qual[cluster]=q
        assert m['status']==q['status']=='complete' and q['method_FP_not_measured']
        for d in q['diagnostics']:inputs.append(merged_diagnostic(cluster,m,q,d))
        if not q['eligible_for_method_comparison']:continue
        for seed in SEEDS:
            w=json.loads((OLD/f'results/{cluster}_{seed}.json').read_text());assert w['status']=='complete';workers.append(w)
            for r in w['rows']:
                assert r['member_fn']==r['final_member_cache_hits']==0 and r['auxiliary_total_bytes']<=r['budget_kib']*1024 and r['required_extra_index_bytes']==0
                assert r['filter_bytes']==sum(r[k] for k in ('model_payload_bytes','bf_payload_bytes','routing_bytes','header_bytes','cache_physical_bytes'))
                assert r['mixed_backend_calls']==r['fp']+w['tail_mixed_members']
                rows.append(dict(cluster=cluster,seed=seed,tail_negative_queries=w['tail_negative_queries'],tail_mixed_queries=w['tail_mixed_queries'],tail_mixed_members=w['tail_mixed_members'],**r))
    groups={}
    for r in rows:groups.setdefault((r['cluster'],r['seed'],r['budget_kib']),{})[r['method']]=r
    for g in groups.values():assert set(g)==set(METHODS)
    comp={}
    for cluster in CLUSTERS:
        cc=[g for k,g in groups.items() if k[0]==cluster]
        if cc:comp[cluster]={base:paired([(g['RA6-Exact128']['fp'],g[base]['fp']) for g in cc]) for base in ('BF+Exact128','Replay','RA-global','Gama')}
    global_comp={base:paired([(g['RA6-Exact128']['fp'],g[base]['fp']) for g in groups.values()]) for base in ('BF+Exact128','Replay','RA-global','Gama')}
    write_csv('qualification.csv',inputs);write_csv('main.csv',rows)
    summary=dict(status='verified',main_rows=len(rows),paired_case_keys=len(groups),fixed_candidates=list(CLUSTERS),eligible_clusters=[c for c in CLUSTERS if qual[c]['eligible_for_method_comparison']],comparisons=comp,global_comparisons=global_comp,all_member_FN=0,required_extra_member_index_bytes=0,original_production_NotFound_evidence=False,original_report_failed=True,original_method_results_changed=False,worker_wall_s=sum(w['wall_s'] for w in workers),report_s=time.perf_counter()-start)
    save('summary.json',summary);save('verification.json',dict(**summary,worker_hashes={f'{w["cluster"]}_{w["seed"]}.json':sha(OLD/f'results/{w["cluster"]}_{w["seed"]}.json') for w in workers}))
    text=['# Round44：真实Twitter请求驱动的检查点目录（报告v2）','','原下载/解析/9个方法worker完成；原report因重复members字段失败，旧失败记录保留。这里仅修报告合并，不重跑任何方法，不改旧FP/配置/流/时间。','','## 数据资格与语义','','这是prefix-only曾见key静态检查点任务，不是原生产KV的Found/NotFound。目录来自前25%GET，接着25%learning、后50%tail；保留记录顺序，不用未来补目录。3个文件事前固定，各100万条原记录；不是完整一周数据。','','| cluster | members | 新key数量 | 样本GET时间范围(seconds) | 时间回退 | AUC16中位 | 特征重叠中位 |','| --- | ---: | ---: | --- | ---: | ---: | ---: |']
    for c in CLUSTERS:
        m=metas[c];ds=qual[c]['diagnostics'];text.append(f'| {c} | {m["members"]} | {m["distinct_negative_keys"]} | {m["minimum_GET_timestamp"]}–{m["maximum_GET_timestamp"]} | {m["GET_time_reversals"]} | {statistics.median(d["development_auc16"] for d in ds):.6f} | {statistics.median(d["query_feature_overlap_fraction"] for d in ds):.6f} |')
    text+=['','所有3cluster通过事前规模门槛。开发AUC/重复差仅解释，不用于剔除不利cluster。负训练/验证keys只从learning阶段首次出现者抽取，query keys互斥；其请求按协议从评估池剔除，未重排其他请求。','','## RA完整配对结果','','| cluster | case keys | vs BF 胜/平/负 | 平滑比中位 | vs Replay 胜/平/负 | 平滑比中位 |','| --- | ---: | --- | ---: | --- | ---: |']
    for c,cc in comp.items():
        b=cc['BF+Exact128'];r=cc['Replay'];text.append(f'| {c} | {b["cases"]} | {b["wins"]}/{b["ties"]}/{b["losses"]} | {b["median_smoothed_ratio"]:.6f} | {r["wins"]}/{r["ties"]}/{r["losses"]} | {r["median_smoothed_ratio"]:.6f} |')
    text+=['','## 全部预算、全部方法FP（3seed各自中位）','','| cluster | KiB | Gama | Replay | RA-global | RA | BF+Exact | PlainBF | ZGate |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for c in comp:
        for budget in sorted({r['budget_kib'] for r in rows if r['cluster']==c}):
            vals=[statistics.median(r['fp'] for r in rows if r['cluster']==c and r['budget_kib']==budget and r['method']==m) for m in METHODS]
            text.append('| '+c+' | '+str(budget)+' | '+' | '.join(map(str,vals))+' |')
    text+=['','## 缓存、便宜规则与解释边界','','| cluster/seed | 负tail请求 | 长度支持规则可拒绝 | 自然混合tail member比例 |','| --- | ---: | ---: | ---: |']
    for w in workers:text.append(f'| {w["cluster"]}/{w["seed"]} | {w["tail_negative_queries"]} | {w["cheap_length_support"]["negative_rejects"]} | {w["tail_mixed_members"]/w["tail_mixed_queries"]:.6f} |')
    text+=['','Exact128存完整匿名key，hash不作cache相等身份，>128bytes绕过；前端全字节计费，额外成员索引0，全部member静态及最终cache检查0FN。此正确性以同版本静态目录和精确反馈为前提，不是动态去重保证。','','回放用预计算features/flags，因此不是SQL/网络端到端延迟。更多FP通常意味着更多backend调用，但时间结论还要另测；不把第43轮合成时延嫁接这里。多个seed/预算共享sample，不是独立应用。3个预选cluster是有限样本，不是对所有生产cache的结论。','','真实请求不会自动让构造标签变成原生产存在性标签。本任务体现真实身份/重复/局部性在一个明确静态目录上的表现；不证明Twitter需要学习过滤器、不把cache miss或value size0当原backend不存在。匿名化仅保留部分结构；模型弱可能反映这种表示/任务，不代表原始业务语义一定不可学习。','','报告所有预选样本，未看到效果后换cluster/改特征/改tail/降门槛。源码冻结保持，论文未动，结果未自动push。来源及许可见原轮SOURCE.md。','']
    with (ROOT/'results/report.md').open('x') as f:f.write('\n'.join(text))
    check();print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':report()

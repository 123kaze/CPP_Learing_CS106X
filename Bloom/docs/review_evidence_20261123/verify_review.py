"""Read-only old archives; create fresh review tables without rerunning frozen reports."""
from pathlib import Path
import csv,json,hashlib,time,math
ROOT=Path(__file__).resolve().parent;BLOOM=ROOT.parents[1];WR=BLOOM/'windows_research'
SOURCES={}

def read(path,kind='json'):
    data=path.read_bytes();SOURCES[str(path.relative_to(BLOOM))]=hashlib.sha256(data).hexdigest()
    return json.loads(data) if kind=='json' else list(csv.DictReader(data.decode().splitlines()))

def save(name,data):
    with (ROOT/name).open('x') as f:json.dump(data,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

def main():
    start=time.perf_counter();affected=read(WR/'round18_gt_audit/results/affected_cases.json')
    expected={(r['dataset'],r['budget_kib'],r['workload'],r['seed']) for r in affected};assert len(expected)==14
    selected=read(WR/'round19_gt_fix/results/selected_comparisons.csv','csv');selected=[r for r in selected if r['method']=='RA6'];assert len(selected)==28
    rows=[]
    for dataset in ('cod','url','caida','shalla'):
        for mode in ('index','fp64'):
            rerun=read(WR/f'round19_gt_fix/results/rerun_{dataset}_{mode}.json');assert rerun['status']=='complete'
            for case in rerun['cases']:
                key=(dataset,case['budget_kib'],case['workload'],case['seed']);assert key in expected
                item=case['methods']['RA6'];old,new=item['old'],item['repaired'];assert item['old_matches_archive']
                folder='round6_bucket/results/main' if mode=='index' else 'round10_fpcache/results/main'
                archive=read(WR/f'{folder}/rows_{dataset}_{case["budget_kib"]}.csv','csv')
                a=next(r for r in archive if r['workload']==case['workload'] and int(r['seed'])==case['seed'] and r['method']==('RA6' if mode=='index' else 'RA6-fp64'))
                assert int(a['fp_tail'])==old['fp'] and int(a['trees'])==old['trees'] and int(a['cache_alloc_bytes'])==old['cache_bytes'] and int(a['total_bytes'])==old['total_bytes']
                if mode=='index':assert int(old['frac']*case['budget_kib']*1024)==int(a['cache_reserved_bytes'])
                else:assert float(a['frac'])==old['frac']
                c=next(r for r in selected if (r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']),r['cache'])==(*key,mode))
                assert int(c['old_fp'])==old['fp'] and int(c['repaired_fp'])==new['fp']
                rows.append(dict(dataset=dataset,budget_kib=case['budget_kib'],workload=case['workload'],seed=case['seed'],cache=mode,old_trees=old['trees'],new_trees=new['trees'],old_frac=old['frac'],new_frac=new['frac'],old_cache_bytes=old['cache_bytes'],new_cache_bytes=new['cache_bytes'],old_total_bytes=old['total_bytes'],new_total_bytes=new['total_bytes'],old_fp=old['fp'],new_fp=new['fp'],delta_fp=new['fp']-old['fp'],same_payload=old['payload_sha256']==new['payload_sha256'],old_payload_sha256=old['payload_sha256'],new_payload_sha256=new['payload_sha256']))
    assert len(rows)==28 and {(r['dataset'],r['budget_kib'],r['workload'],r['seed']) for r in rows}==expected
    with (ROOT/'gt19_14_cases.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    mainrows=read(WR/'round19_gt_fix/results/updated_main_comparisons.csv','csv');stats={}
    for mode in ('index','fp64'):
        rr=[r for r in mainrows if r['cohort']=='main' and r['cache']==mode and r['workload']!='探测重放10%'];assert len(rr)==1076
        for stage in ('old_ra_fp','repaired_ra_fp'):
            stats[mode+'/'+stage]=dict(cases=len(rr),wins=sum(int(r[stage])<int(r['bf_cache_fp']) for r in rr),ties=sum(int(r[stage])==int(r['bf_cache_fp']) for r in rr),losses=sum(int(r[stage])>int(r['bf_cache_fp']) for r in rr))
    accounting=read(WR/'round39_deployment_accounting/results/call_accounting.csv','csv')
    example=[r for r in accounting if r['dataset']=='mawi2021_flow' and r['cache']=='index' and int(r['budget_kib'])==24];assert len(example)==3
    breakeven=[]
    for r in example:
        L,H,extra,saved=[int(r[k]) for k in ('learning_queries','tail_queries','extra_learning_backend_calls','tail_backend_calls_saved')]
        assert int(r['net_backend_calls_saved_after_one_window'])==saved-extra
        q=extra*H/saved if saved>0 else None
        if q is not None:assert math.isclose(q,float(r['backend_only_break_even_negative_queries']),rel_tol=1e-12)
        breakeven.append(dict(comparison=r['comparison'],L=L,H=H,extra_learning_calls=extra,tail_saved_calls=saved,net_calls_saved=saved-extra,break_even_future_negative_queries=math.ceil(q) if q is not None else None,tail_window_multiples=q/H if q is not None else None,assumptions='stationary observed saving rate; lookup calls only; excludes CPU/training/index/reconfiguration; starts after learning'))
    changed={m:sum(r['delta_fp']!=0 for r in rows if r['cache']==m) for m in ('index','fp64')}
    save('verification.json',dict(status='verified',gt19_case_keys=14,cache_specific_rows=28,fp_changed_per_format=changed,full1076=stats,mawi21_call_break_even=breakeven,sources=SOURCES,seconds=time.perf_counter()-start,third_party_rerun=False,old_reports_rewritten=False))
    lines=['# GT19的14例旧/新差分、完整1076例与代表性回本量','','仅从归档只读复算，不重跑/改写冻结实验，也不是第三方独立复现。来源SHA见verification.json。旧RA主表逐项匹配28条重算记录；index/fp64分开展示。','','## 14个case keys，每格式各14条','','| 数据 | KiB | 工作负载 | seed | cache | 树old→new | 份额old→new | FP old→new | ΔFP |','| --- | ---: | --- | ---: | --- | --- | --- | --- | ---: |']
    for r in rows:lines.append(f'| {r["dataset"]} | {r["budget_kib"]} | {r["workload"]} | {r["seed"]} | {r["cache"]} | {r["old_trees"]}→{r["new_trees"]} | {r["old_frac"]}→{r["new_frac"]} | {r["old_fp"]}→{r["new_fp"]} | {r["delta_fp"]:+d} |')
    lines+=['','每格式均5/14例FP改变；相同树数/份额不保证位图相同。完整物理字节及payload SHA在CSV。GT19只处理c>=2且下一频数bin为空的回退，singleton规则不变；不是概率归一化变体。旧MAWI24数据/版本归属不变，不把事后补测包装成新holdout。','','## 不去掉低FP案例的1076主比较','','| 格式/版本 | 胜 | 平 | 负 |','| --- | ---: | ---: | ---: |']
    for key,r in stats.items():lines.append(f'| {key} | {r["wins"]} | {r["ties"]} | {r["losses"]} |')
    lines+=['','这些1076例仍排除原70个probe replay；不是所有可能工作负载，更不是1076独立自然流。纳入低FP后计数不等于大效应；不改统计分组追求显著性。','','## MAWI21 index24KiB：调用数级回本','','| baseline | 额外学习调用 | 一段tail节省 | 净节省 | 学完后的回本negative查询量 | 原tail倍数 |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in breakeven:lines.append(f'| {r["comparison"]} | {r["extra_learning_calls"]} | {r["tail_saved_calls"]} | {r["net_calls_saved"]} | {r["break_even_future_negative_queries"]} | {r["tail_window_multiples"]:.6f} |')
    lines+=['','未来negative查询量从学习结束后计，不含之前学习L。按观测tail节省率恒定且只计lookup调用外推；不是观察了这么长的未来流，不包括训练、模型/特征、索引和重建。因此只是理想化必要账本，不能当真实时间回本。共享标签时增量学习lookup为0，表中0也不代表训练成本为0。成员比例p>0时转换总查询量需除以1-p。','','完整时间条件为ΔT(N)=A+ΔL*C/1e6+N[d-(1-p)sC]/1e6。只有(1-p)sC>d才有持续收益；重建重复计A和ΔL。没有测量的A/C/d不能填成生产数字。第42轮另测raw-key SQLite查询和训练准备；不能把MAWI的s和ClarkNet的时延拼成一个实测系统。','','旧fp64档案中的概率字段仍受第40轮勘误约束，本次只复算FP/选择，不恢复S/2^64的错误通用保证。','']
    with (ROOT/'report.md').open('x') as f:f.write('\n'.join(lines))
    print(json.dumps(dict(changed=changed,full1076=stats,break_even=breakeven),ensure_ascii=False,indent=2))

if __name__=='__main__':main()

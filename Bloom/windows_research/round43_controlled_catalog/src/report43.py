import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from catalog43 import *
import csv,statistics,math


def csv_out(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/'results'/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()})


def summary_pair(rows,a,b):
    group={}
    for r in rows:group.setdefault((r['strength'],r['seed'],r['association'],r['budget_kib']),{})[r['method']]=r
    pairs=[(g[a]['fp'],g[b]['fp']) for g in group.values()]
    return dict(cases=len(pairs),wins=sum(a<b for a,b in pairs),ties=sum(a==b for a,b in pairs),losses=sum(a>b for a,b in pairs),median_smoothed_ratio=statistics.median((a+1)/(b+1) for a,b in pairs))


def report():
    check();workers=[json.loads((ROOT/f'results/a{a}_s{s}.json').read_text()) for a in STRENGTHS for s in SEEDS]
    assert all(w['status']=='complete' and not w['pilot'] and len(w['cases'])==9 for w in workers)
    rows=[];controlled=[];timings=[];costs=[];predictions=[];diagnostics=[]
    for w in workers:
        for case in w['cases']:
            key=dict(strength=w['strength'],seed=w['seed'],association=case['association'],budget_kib=case['budget_kib'])
            by={r['method']:r for r in case['rows']};assert set(by)==set(METHODS)
            for r in case['rows']:
                assert r['member_fn']==0 and r['total_bytes']<=case['budget_kib']*1024 and r['required_backend_index_bytes']==0
                rows.append(dict(**key,**r))
            ctrl=case['controls'];assert ctrl['status']=='complete' and len(ctrl['rows'])==3
            for r in ctrl['rows']:
                assert r['member_fn']==0 and r['total_bytes']<=case['budget_kib']*1024
                controlled.append(dict(**key,**r,trees=ctrl['trees'],cache_bytes=ctrl['cache_bytes'],bf_bits=ctrl['bf_bits'],conditional_interior=ctrl['conditional_identity']['interior'],conditional_AMGM_factor=ctrl['conditional_identity']['arithmetic_geometric_factor'],actual_clock_fixed_T=False))
            diagnostics.append(dict(**key,development_auc16=w['training']['development_auc_by_trees']['16'],support_rule_tail_fp=case['feature_support_baseline']['fp'],tail_queries=case['tail_queries'],regions=case['stream']['regions'],zgate_winner=case['selection']['zgate_winner']))
            for t in case['timings']:
                assert t['member_fn']==0 and t['reference_equal']
                timings.append(dict(**key,**t))
            for p in (.1,.9):
                rr=[r for r in case['timings'] if r['member_target']==p];lookup={(r['method'],r['rep']):r for r in rr};assert len(lookup)==12
                for baseline in ('BF+Cache','Replay','NoFilter'):
                    ra=[lookup['RA6',rep] for rep in range(3)];base=[lookup[baseline,rep] for rep in range(3)]
                    assert len({r['backend_calls'] for r in ra})==1 and len({r['backend_calls'] for r in base})==1
                    calls_saved=base[0]['backend_calls']-ra[0]['backend_calls']
                    delta_ns=statistics.median(a['elapsed_ns']-b['elapsed_ns'] for a,b in zip(ra,base))
                    paired_ratio=statistics.median(a['elapsed_ns']/b['elapsed_ns'] for a,b in zip(ra,base))
                    positive_crossover=max(0.,delta_ns/1000/calls_saved) if calls_saved>0 else None
                    train=w['training'];shared=train['training_s']+train['score_s']+train['shared_tree_s']
                    rp=case['query_preparation']['executables']['RA6'];startup_ra=shared+case['GT_summary_s']+by['RA6']['selection_build_s']+rp['executable_rebuild_s']
                    startup_base=0. if baseline=='NoFilter' else by[baseline]['selection_build_s']+case['query_preparation']['executables'][baseline]['executable_rebuild_s']+(shared if baseline=='Replay' else 0.)
                    dstart=startup_ra-startup_base
                    row=dict(**key,member_target=p,baseline=baseline,queries=ra[0]['queries'],actual_members=ra[0]['actual_members'],ra_backend_calls=ra[0]['backend_calls'],baseline_backend_calls=base[0]['backend_calls'],backend_calls_saved=calls_saved,measured_window_delta_s=delta_ns/1e9,median_paired_time_ratio=paired_ratio,additional_backend_us_for_query_crossover=positive_crossover,extra_accounted_startup_s=dstart,projection_not_backend_measurement=True)
                    costs.append(row)
                    for add in (0,5,20,100):
                        qdelta=delta_ns/1e9-calls_saved*add/1e6;net=dstart+qdelta
                        benefit_per_query=-qdelta/ra[0]['queries']
                        n=math.ceil(max(0.,dstart)/benefit_per_query) if benefit_per_query>0 else None
                        predictions.append(dict(**key,member_target=p,baseline=baseline,additional_backend_us=add,projected_query_delta_s=qdelta,projected_startup_plus_one_window_delta_s=net,conditional_break_even_future_queries=n,assumption='observed finite-window rates persist; shared labels; extra lookup cost additive; not measured remote latency'))
    assert len(rows)==378 and len(controlled)==162 and len(timings)==1296 and len(costs)==324 and len(predictions)==1296
    csv_out('main.csv',rows);csv_out('controls.csv',controlled);csv_out('timings.csv',timings);csv_out('cost_crossovers.csv',costs);csv_out('cost_projections.csv',predictions);csv_out('diagnostics.csv',diagnostics)
    result={}
    for a in STRENGTHS:
        for assoc in ASSOCIATIONS:
            rr=[r for r in rows if r['strength']==a and r['association']==assoc]
            result[f'a{a}/{assoc}']={b:summary_pair(rr,'RA6',b) for b in ('BF+Cache','Replay','RA-global','Gama')}
    global_pairs={b:summary_pair(rows,'RA6',b) for b in ('BF+Cache','Replay','RA-global','Gama')}
    actual={}
    for a in STRENGTHS:
        for p in (.1,.9):
            rr=[r for r in costs if r['strength']==a and r['member_target']==p and r['baseline']=='BF+Cache']
            actual[f'a{a}/p{p}']=dict(cases=len(rr),wins=sum(r['median_paired_time_ratio']<1 for r in rr),losses=sum(r['median_paired_time_ratio']>1 for r in rr),median_paired_ratio=statistics.median(r['median_paired_time_ratio'] for r in rr),positive_call_saving_cases=sum(r['backend_calls_saved']>0 for r in rr))
    summary=dict(status='verified',main_rows=len(rows),control_rows=len(controlled),query_timings=len(timings),global_FP=global_pairs,FP_by_controlled_family=result,actual_local_SQL_RA_vs_BF=actual,worker_wall_s=sum(w['wall_s'] for w in workers),synthetic=True,production_trace=False,all_member_FN=0,extra_backend_index_bytes=0)
    W.save(ROOT/'results/summary.json',summary);W.save(ROOT/'results/verification.json',dict(**summary,worker_sha256={f'a{w["strength"]}_s{w["seed"]}.json':W.sha(ROOT/f'results/a{w["strength"]}_s{w["seed"]}.json') for w in workers}))
    text=['# Round43：受控目录条件实验（不是生产轨迹）','','完整54case keys，378条主比较、162条固定配置控制、1296次真实本机SQLite查询窗口计时。按预设强度/关联/预算/seed完整执行，不按tail挑赢家。','','## RA的完整FP对照','','| 特征强度/关联 | vs BF 胜/平/负 | RA/BF平滑比中位 | vs Replay 胜/平/负 | RA/Replay比 |','| --- | --- | ---: | --- | ---: |']
    for family,comp in result.items():
        b=comp['BF+Cache'];r=comp['Replay'];text.append(f'| {family} | {b["wins"]}/{b["ties"]}/{b["losses"]} | {b["median_smoothed_ratio"]:.6f} | {r["wins"]}/{r["ties"]}/{r["losses"]} | {r["median_smoothed_ratio"]:.6f} |')
    text+=['','## 实际本机SQLite完整路径（RA vs BF+Cache）','','| 强度/member目标比例 | 胜/负 | 配对耗时比中位 | 少查backend的设置数 |','| --- | --- | ---: | ---: |']
    for family,r in actual.items():text.append(f'| {family} | {r["wins"]}/{r["losses"]} | {r["median_paired_ratio"]:.6f} | {r["positive_call_saving_cases"]}/{r["cases"]} |')
    text+=['','## Interpretation and limits','', 'The raw domain really is uint64. Full64-bit bijective hashes in cache are exact key representations, not generic compressed-string fingerprints. No member index, no probabilistic FN guarantee invoked. Input/source models/queries are synthetic and deliberately vary feature learnability and popularity correlation. Labels are not read by the online query path. All three correlation arms have identical regional traffic masses; only within-region rank concentration differs. Strong-model results do not establish that production workloads share that distribution.','','Actual query timers include8byte decode, bijective hash, cache, top8feature extraction, model, packed BF, actualSQL and negative feedback. NoFilter avoids unused preprocessing. Warm local SQLite is not remote/productionKV. Two chosen member proportions are experimental parameters, not measured workload statistics. Fixed20000query windows are NOT the750000negative-query FP table. Queries/seed/budgets share catalogue inputs, so no independent-sample p-values are reported.','','cost_crossovers.csv derives the EXTRA additive backend lookup cost at which measured query differences would cross, only if RA saves calls. cost_projections.csv values at0/5/20/100us are NOT timing measurements, not a discovered deployment and not an excuse to call an FP loss a win. Startup is separately accounted from model/score/tree/GT/selection/executable rebuild, with common input/DB/JIT outside; shared-label assumption is explicit. Long-run break-even requires stationary measured rates and does not validate dynamic rebuilds.','','Fixed-config controls hold anchor trees/partition/cache/BFbits fixed and compare h/traffic/miss. Conditional AMGM is recorded only with its support/interiority conditions; actual CLOCK does not holdT exogenous, so failures do not falsify that restricted theorem. FullRA6 still changes partitions/configurations and is heuristic. ZGate learning-only selection is a labeled variant, not a future guarantee or free speedup.','','All development and query feature support, AUC and bin-presence-rule results are in diagnostics/workerJSON. A generator branch knows which catalogue it is generating; no deployment decision may use that construction label. Reproducible by frozen code/seeds; no new real-workload claim, no manuscript modification.','']
    (ROOT/'results/report.md').write_text('\n'.join(text));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':report()

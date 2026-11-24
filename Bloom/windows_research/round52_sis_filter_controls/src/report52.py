import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker52 import ROOT,WR,check,save,sha,RECIPES,SEEDS,METHODS
import json,csv,statistics


def write_csv(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/'results'/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in r.items()})


def paired(pairs):
    return dict(cases=len(pairs),wins=sum(a<b for a,b in pairs),ties=sum(a==b for a,b in pairs),losses=sum(a>b for a,b in pairs),median_smoothed_ratio=statistics.median((a+1)/(b+1) for a,b in pairs))


def report():
    check();workers=[json.loads((ROOT/f'results/{recipe}_{seed}.json').read_text()) for recipe in RECIPES for seed in SEEDS];assert all(w['status']=='complete' and not w['pilot'] and len(w['rows'])==21 and len(w['controls'])==3 for w in workers)
    rows=[];controls=[];groups={}
    for w in workers:
        for r in w['rows']:
            assert r['member_fn']==0 and r['required_extra_index_bytes']==0 and r['filter_bytes']==r['auxiliary_total_bytes']<=r['budget_kib']*1024
            assert r['filter_bytes']==sum(r[k] for k in ('model_payload_bytes','bf_payload_bytes','routing_bytes','header_bytes','cache_physical_bytes'))
            x=dict(recipe=w['recipe'],seed=w['seed'],learning_queries=w['learning_queries'],tail_queries=w['tail_queries'],evaluation_pool_retained_request_fraction=w['evaluation_pool_retained_request_fraction'],**r);rows.append(x);groups.setdefault((w['recipe'],w['seed'],r['budget_kib']),{})[r['method']]=x
        for c in w['controls']:
            for r in c['rows']:
                assert r['member_BF_FN']==r['final_member_cache_hits']==0 and r['total_bytes']<=c['budget_kib']*1024
                controls.append(dict(recipe=w['recipe'],seed=w['seed'],budget_kib=c['budget_kib'],trees=c['trees'],cache_bytes=c['cache_bytes'],bf_bits=c['bf_bits'],conditional_interior=c['conditional_identity']['interior'],conditional_AMGM_factor=c['conditional_identity']['arithmetic_geometric_factor'],actual_CLOCK_fixed_T=False,**r))
    assert len(rows)==126 and len(controls)==54 and len(groups)==18
    for g in groups.values():
        assert set(g)==set(METHODS);z=g['ZGate-Exact128'];winner=g['BF+Exact128' if z['selection_info']['winner']=='BF' else 'RA6-Exact128']
        for field in ('fp','trees','cache_frac','filter_bytes','flags_sha256','cache_sha256'):assert z[field]==winner[field]
    for seed in SEEDS:
        for budget in (672,1343,2685):
            for method in ('BF+Exact128','PlainBF'):
                a=groups['original',seed,budget][method];b=groups['balanced_clip',seed,budget][method]
                for field in ('fp','trees','cache_frac','filter_bytes','flags_sha256','cache_sha256'):assert a[field]==b[field],(seed,budget,method,field)
    pilot=json.loads((ROOT/'results/pilot.json').read_text());formal=next(w for w in workers if w['recipe']=='balanced_clip' and w['seed']==5001)
    for a in pilot['rows']:
        b=next(r for r in formal['rows'] if r['budget_kib']==a['budget_kib'] and r['method']==a['method'])
        for field in ('fp','trees','cache_frac','filter_bytes','flags_sha256','cache_sha256'):assert a[field]==b[field]
    compare={};fixed={};select={}
    for recipe in RECIPES:
        gg={k:g for k,g in groups.items() if k[0]==recipe};compare[recipe]={base:paired([(g['RA6-Exact128']['fp'],g[base]['fp']) for g in gg.values()]) for base in ('BF+Exact128','Replay','RA-global','Gama')}
        cc={}
        for r in controls:
            if r['recipe']==recipe:cc.setdefault((r['seed'],r['budget_kib']),{})[r['arm']]=r['fp']
        fixed[recipe]={b:paired([(x['miss'],x[b]) for x in cc.values()]) for b in ('h','traffic')}
        ratios=[(g['RA6-Exact128']['selection_build_s']+g['RA6-Exact128']['summary_charged_s'])/(g['Replay']['selection_build_s']+g['Replay']['summary_charged_s']) for g in gg.values()]
        select[recipe]=dict(cases=len(ratios),RA_faster=sum(x<1 for x in ratios),median_RA_over_Replay=statistics.median(ratios))
    summary=dict(status='verified',main_rows=126,control_rows=54,case_keys=18,comparisons=compare,fixed_controls=fixed,selection=select,BF_controls_recipe_invariant=True,pilot_non_timing_reproduced=True,all_member_FN=0,extra_index_bytes=0,worker_wall_s=sum(w['wall_s'] for w in workers),exploratory_not_independent_holdout=True,end_to_end_SQL_measured=False)
    write_csv('main.csv',rows);write_csv('controls.csv',controls);save(ROOT/'results/summary.json',summary);save(ROOT/'results/verification.json',dict(**summary,worker_sha256={f'{w["recipe"]}_{w["seed"]}.json':sha(ROOT/f'results/{w["recipe"]}_{w["seed"]}.json') for w in workers}))
    text=['# Round52：SIS实体filter结果，原/稳定训练配方并列','','完整126主比较/54固定配置控制；不是独立holdout，不是端到端部署计时。真实线上文件来自SIS，但任务是observed-success/404的回溯稳定子集，不能推出业务record存在性。','','## 完整主比较','','| recipe | RA vs BF 胜/平/负 | 平滑比中位 | RA vs Replay 胜/平/负 | 平滑比中位 |','| --- | --- | ---: | --- | ---: |']
    for recipe in RECIPES:
        b=compare[recipe]['BF+Exact128'];r=compare[recipe]['Replay'];text.append(f'| {recipe} | {b["wins"]}/{b["ties"]}/{b["losses"]} | {b["median_smoothed_ratio"]:.6f} | {r["wins"]}/{r["ties"]}/{r["losses"]} | {r["median_smoothed_ratio"]:.6f} |')
    text+=['','## 每预算三seed的FP中位数（不是配对比）','','| recipe | KiB | Gama | Replay | RA-global | RA | BF+Exact | PlainBF | ZGate |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for recipe in RECIPES:
        for budget in (672,1343,2685):
            values=[statistics.median(groups[recipe,seed,budget][method]['fp'] for seed in SEEDS) for method in METHODS]
            text.append('| '+recipe+' | '+str(budget)+' | '+' | '.join(map(str,values))+' |')
    text+=['','## 必须保留的限制','','- balanced_clip是开发段选择的显式新训练配方，同时给所有learned基线，原配方完整保留；BF两配方的结构/FP/最终cache完全一致。不是只给RA更强模型。','- 每配方按实际训练树数报告可行网格；无法训练的prefix不补树、不伪造结果。已有原RA6/GT19/MAWIholdout不被改写。','- 完整input/训练/score/tree/GT/JIT/选择/回放/成员检查分开计时；回放用预计算flags，不是模型/特征/SQL服务时间。','- Exact128严格完整key相等、长key绕过；额外memberhash验证索引0。RA原预测未建模长keybypass，局限保留。','- negative train/val key排除改变各seed评估请求量，尤其seed5002移除了主要热点；所有seed都保留，不能将行数当独立工作负载。','- 全文件HTTP负请求比例很低，负流FP改善不自动覆盖全量query推理、训练、标签或重配置成本。','- 固定h/traffic/miss控制与完整RA配置选择不同；AMGM只对应其正支持/未截断/固定T条件，actual CLOCK的T不是外生。','- ZGate仅保证learning finalist比较，额外回放与两类搜索计费，不保证未来不退化。','- 前200万行失败资格保持，完整文件属于后来明确标注的探索；六月/其他来源还不是已执行独立确认性验证。','- 不改论文、不自动push，所有负方向与可能的失败保留。','']
    with (ROOT/'results/report.md').open('x') as f:f.write('\n'.join(text))
    check();print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':report()

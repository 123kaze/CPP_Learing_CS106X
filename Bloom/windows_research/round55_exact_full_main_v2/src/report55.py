"""Verify full archived-key coverage and emit exact-only table/figure source data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common55 import *
from collections import defaultdict
from scipy.stats import spearmanr


def csvout(name,rows):
    p=ROOT/'results'/name;fields=sorted(set().union(*(r.keys() for r in rows)))
    with p.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})


def group(name):
    if name=='真实轨迹':return 'trace'
    if name==E5.PROBE:return 'probe'
    if name in ('每key一次','全新对抗'):return 'no-repeat'
    return name.rsplit('-',1)[-1]


def main():
    freeze_check();start=time.perf_counter();manifest=case_manifest();cases=[];rows=[];abl=[];rank=[];pred=[];seen=set()
    for setting in manifest['settings']:
        ds,k=setting['dataset'],setting['budget_kib'];folder=ROOT/f'results/{ds}_{k}';meta=json.loads((folder/'status.json').read_text());assert meta['status']=='complete'
        assert meta['cases_completed']==len(setting['cases']) and meta['peak_rss_bytes']<4*1024**3
        for name,expected in zip(meta['case_files'],setting['cases']):
            item=json.loads((folder/name).read_text());assert item['status']=='complete' and item['case']==expected
            key=ds,k,expected['workload'],expected['seed'];assert key not in seen;seen.add(key)
            base={field:expected[field] for field in ('dataset','budget_kib','workload','seed','cohort')}
            rr={r['method']:r for r in item['rows']};assert len(rr)==14 and all(m in rr for m in MAIN)
            for r in item['rows']:
                assert r['member_fn']==0 and r['member_index_bytes']==0 and r['total_bytes']<=k*1024
                rows.append(dict(cohort=expected['cohort'],**r))
            for a in item['ablations']:assert a['member_fn']==a['member_index_bytes']==0 and a['total_bytes']<=k*1024
            assert len(item['ablations'])==(6 if expected['seed']<=2 else 0)
            abl.extend(dict(**base,reference_stage1_fp=rr['RA-stage1']['fp'],**a) for a in item['ablations'])
            ref=item['hindsight_h_fp'] if item['hindsight_h_fp'] is not None else rr['Replay']['fp']
            case=dict(**base,group=group(expected['workload']),reference_fp=ref,eligible_reference30=ref>=30,hindsight_h_fp=item['hindsight_h_fp'],learning_queries=item['learning_queries'],tail_queries=item['tail_queries'],learning_sha=item['learning_sha'],base_tail_sha=item['base_tail_sha'],case_wall_s=item['wall_s'])
            for m,r in rr.items():case[m]=r['fp']
            case.update(RA_Replay_ratio=(rr['RA6']['fp']+1)/(rr['Replay']['fp']+1),RA_BF_ratio=(rr['RA6']['fp']+1)/(rr['BF+Exact']['fp']+1),RA_Gama_ratio=(rr['RA6']['fp']+1)/(rr['Gama']['fp']+1))
            cases.append(case)
            for r in item['top10']:rank.append(dict(**base,**r))
            for r in item['weighted_full']:pred.append(dict(**base,**r))
    assert len(cases)==1150 and sum(c['cohort']=='main' for c in cases)==1146
    assert sum(c['cohort']=='main' and c['group']=='probe' for c in cases)==70 and len(rows)==16100
    for f,r in [('rows.csv',rows),('cases.csv',cases),('ablations.csv',abl),('top10_predictions.csv',rank),('full_weighted_predictions.csv',pred)]:csvout(f,r)
    total=[]
    for st in manifest['settings']:
        selected=[c for c in cases if c['dataset']==st['dataset'] and c['budget_kib']==st['budget_kib'] and c['group']!='probe']
        by=defaultdict(list)
        for c in selected:by[c['workload']].append(c)
        for m in MAIN+('RA6-warm','Replay-warm','BF+Exact-warm','Learned-stacked'):
            total.append(dict(dataset=st['dataset'],budget_kib=st['budget_kib'],method=m,workloads=len(by),cases=len(selected),FP_sum_of_seed_means=sum(float(np.mean([c[m] for c in values])) for values in by.values())))
    csvout('table_main_totals.csv',total)
    summary={}
    for cohort in ('all_nonprobe','eligible30_nonprobe','probe','MAWI24'):
        selected=[c for c in cases if (c['cohort']=='previously_used_MAWI24' if cohort=='MAWI24' else c['cohort']=='main' and (c['group']=='probe' if cohort=='probe' else c['group']!='probe') and (c['eligible_reference30'] if cohort=='eligible30_nonprobe' else True))]
        stats={}
        for baseline in ('Gama','Replay','BF+Exact','RA-global'):
            ratio=[(c['RA6']+1)/(c[baseline]+1) for c in selected];worst=max(selected,key=lambda c:(c['RA6']+1)/(c[baseline]+1))
            stats[baseline]=dict(cases=len(selected),wins=sum(c['RA6']<c[baseline] for c in selected),ties=sum(c['RA6']==c[baseline] for c in selected),losses=sum(c['RA6']>c[baseline] for c in selected),median=float(np.median(ratio)),RA_FP_sum=sum(c['RA6'] for c in selected),baseline_FP_sum=sum(c[baseline] for c in selected),worst={k:worst[k] for k in ('dataset','budget_kib','workload','seed','RA6',baseline)})
        summary[cohort]=stats
    paired=[]
    for eligible in (False,True):
        for gr in ('1万','10万','100万','全部','no-repeat','trace'):
            cc=[c for c in cases if c['cohort']=='main' and c['group']==gr and (c['eligible_reference30'] if eligible else True)]
            if not cc:continue
            for m in ('RA-stage1','RA6','RA6-top3','RA6-top10','Gama+10%'):
                v=np.array([(c[m]+1)/(c['Replay']+1) for c in cc]);paired.append(dict(group=gr,eligible30=eligible,method=m,cases=len(cc),p25=float(np.quantile(v,.25)),median=float(np.median(v)),p75=float(np.quantile(v,.75)),worst=float(v.max()),share_le1=float((v<=1).mean())))
    csvout('table_case_ratios.csv',paired)
    verification=dict(status='passed',main_cases=1146,MAWI24_cases=4,main_rows=len(rows),ablations=len(abl),top10_records=len(rank),full_weighted_candidates=len(pred),all_budget_FN_index_checks=True,old_Gama_regressions=1150,summary=summary,report_s=time.perf_counter()-start,not_completed_by_this_stage=['fresh-training construction timing','dedicated 3-rep selection/scalability campaigns','new plotted figures/render inspection','paper editing'])
    save(ROOT/'results/verification.json',verification)
    text=['# 第55轮：完整无索引主FP矩阵','','本轮重新执行原1146case和已见MAWI24四例，不是把第53轮62例复制充数。完整预算/成员FN/原Gama回归通过，完整rawkey cache不依赖成员索引。', '', '| 主1076非probe对照 | 胜/平/负 | 配对平滑比中位 |','| --- | --- | ---: |']
    for m,s in summary['all_nonprobe'].items():text.append(f"| {m} | {s['wins']}/{s['ties']}/{s['losses']} | {s['median']:.6f} |")
    text+=['','所有低FP保留，原reference>=30子集与全量并列；probe70例分开。温cache、learned stacked、seed0全加权候选hindsight、seed0–2消融及全seed top10预测均已记录。见results/*.csv和verification.json。','','重要：本轮仍复用原模型/分数，因此是完整FP/选择逻辑重跑，不是从训练开始的全部construction或服务延迟重测。后续独立计时/scalability和图形渲染尚未完成；不把本轮完成等同“全文表图已统一”。MAWI24是已用数据的事后exact变体，不是新独立holdout。长key绕过/静态同版本/FN保证前提保留。原prefix结果与论文未改，没有自动发布。','']
    (ROOT/'README.md').write_text('\n'.join(text));print('FULL_MAIN_VERIFIED 1146 + 4 cases',flush=True)

if __name__=='__main__':main()

"""Main result tables, five-seed uncertainty and exact paired inference."""
from pathlib import Path
import json,csv,itertools,math,statistics
from collections import defaultdict
import numpy as np
from scipy.stats import t
ROOT=Path(__file__).resolve().parents[1]
def write_csv(name,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/'tables'/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def sign_p(differences):
    d=np.asarray(differences,dtype=float)
    if not len(d) or np.all(d==0):return 1.
    observed=abs(d.mean())
    null=[abs((d*np.array(s)).mean()) for s in itertools.product((-1,1),repeat=len(d))]
    return sum(x>=observed-1e-14 for x in null)/len(null)
def run():
    groups=defaultdict(list);raw=[];status=[]
    for path in sorted((ROOT/'results'/'main').glob('*/*.json')):
        obj=json.loads(path.read_text(encoding='utf-8'))
        status.append(dict(file=str(path.relative_to(ROOT)),completed=obj['completed'],seed_workloads=len(obj['selections']),rows=len(obj['rows'])))
        if not obj['completed']:continue
        raw.extend(obj['rows'])
    for path in sorted((ROOT/'results'/'stacked').glob('*/*.json')):
        obj=json.loads(path.read_text(encoding='utf-8'))
        if not obj['completed']:continue
        assert obj.get('zero_fallback_rechecked') or path.parent.name=='mawi2022_flow'
        for r in obj['rows']:
            raw.append(dict(r,actual_filter_state_bytes=r['state_bytes'],member_index_bytes=0,cache_allocated_bytes=0))
    for row in raw:
        row['required_member_index_bytes']=row['member_index_bytes']+112 if row.get('cache_allocated_bytes',0)>0 else 0
        groups[row['dataset'],row['budget_kib'],row['workload'],row['method']].append(row)
    agg=[]
    for key,values in sorted(groups.items()):
        values=sorted(values,key=lambda r:r['seed']);rates=np.array([r['fpr'] for r in values]);n=len(rates)
        deterministic=key[2]=='全新对抗'
        sd=float(rates.std(ddof=1)) if n>1 else None
        half=float(t.ppf(.975,n-1)*sd/math.sqrt(n)) if n>1 and not deterministic else None
        agg.append(dict(dataset=key[0],budget_kib=key[1],workload=key[2],method=key[3],runs=n,
                        independent_seed_runs=1 if deterministic else n,
                        fpr_mean=float(rates.mean()),fpr_std=sd,
                        ci95_low=max(0.,float(rates.mean())-half) if half is not None else None,
                        ci95_high=min(1.,float(rates.mean())+half) if half is not None else None,
                        fp_mean=statistics.mean(v['fp_tail'] for v in values),
                        filter_state_bytes_max=max(v['actual_filter_state_bytes'] for v in values),
                        allocated_harness_member_index_bytes=values[0]['member_index_bytes']+112 if values[0]['member_index_bytes'] else 0,
                        required_member_index_bytes_max=max(v['required_member_index_bytes'] for v in values),
                        note='Deterministic replay, not five independent replications' if deterministic else 't interval across workload seeds; model and dataset fixed'))
    settings=defaultdict(dict)
    for key,values in groups.items():settings[key[:3]][key[3]]=values
    comparisons=[]
    for key,methods in sorted(settings.items()):
        for baseline in ('Gama','LearnGrid','Fixed48Grid','BFCacheGrid','SkiQFAdmission2','LearnedStacked_LearnTune'):
            if 'StreamModel' not in methods or baseline not in methods:continue
            a={v['seed']:v for v in methods['StreamModel']};b={v['seed']:v for v in methods[baseline]};seeds=sorted(set(a)&set(b))
            diff=np.array([a[s]['fpr']-b[s]['fpr'] for s in seeds]);n=len(diff)
            infer=n==5 and key[2]!='全新对抗'
            se=float(diff.std(ddof=1)/math.sqrt(n)) if infer else None
            mean=float(diff.mean());half=float(t.ppf(.975,n-1)*se) if infer else None
            p=sign_p(diff) if infer else None
            comparisons.append(dict(dataset=key[0],budget_kib=key[1],workload=key[2],baseline=baseline,
                                    paired_seeds=n,delta_fpr_mean=mean,delta_fp_per_million=mean*1e6,
                                    delta_ci95_low=mean-half if half is not None else None,
                                    delta_ci95_high=mean+half if half is not None else None,
                                    smoothed_fp_ratio=(statistics.mean(a[s]['fp_tail'] for s in seeds)+1)/(statistics.mean(b[s]['fp_tail'] for s in seeds)+1),
                                    exact_sign_flip_p=p,holm_p=None,inferential=bool(infer)))
    # Family: all predeclared StreamModel vs Gama/LearnGrid paired tests.
    family=[r for r in comparisons if r['inferential'] and r['baseline'] in ('Gama','LearnGrid')]
    ordered=sorted(family,key=lambda r:r['exact_sign_flip_p']);running=0.
    for i,row in enumerate(ordered):
        running=max(running,(len(ordered)-i)*row['exact_sign_flip_p']);row['holm_p']=min(1.,running)
    write_csv('main_metrics.csv',agg);write_csv('paired_comparisons.csv',comparisons)
    aqfgroups=defaultdict(list)
    for path in (ROOT/'results'/'aqf').glob('*.json'):
        obj=json.loads(path.read_text(encoding='utf-8'));assert obj['completed']
        for r in obj['rows']:aqfgroups[r['dataset'],r['budget_kib'],r['workload']].append(r)
    aqfsummary=[]
    for key,values in sorted(aqfgroups.items()):
        assert all(v['feasible'] and v['fn_before']==v['fn_after']==0 for v in values)
        a=np.array([v['fpr'] for v in values]);b=np.array([v['gama_fp']/v['evaluation_queries'] for v in values]);infer=len(values)==5 and key[2]!='全新对抗'
        half=float(t.ppf(.975,4)*a.std(ddof=1)/np.sqrt(5)) if infer else None
        aqfsummary.append(dict(dataset=key[0],budget_kib=key[1],workload=key[2],runs=len(values),aqf_fpr_mean=float(a.mean()),gama_fpr_mean=float(b.mean()),
                               aqf_ci95_low=max(0.,float(a.mean())-half) if half is not None else None,aqf_ci95_high=min(1.,float(a.mean())+half) if half is not None else None,
                               paired_delta_fpr=float((a-b).mean()),exact_sign_flip_p=sign_p(a-b) if infer else None,
                               filter_allocated_bytes_max=max(v['filter_allocated_bytes'] for v in values),reverse_map_bytes_max=max(v['reverse_map_allocated_bytes'] for v in values)))
    write_csv('aqf_metrics.csv',aqfsummary)
    out=dict(status=status,valid_rows=len(raw),aggregates=agg,comparisons=comparisons,aqf_aggregates=aqfsummary,
             inference_note='Five paired signs have 32 permutations, so the smallest nonzero two-sided p is .0625. No significance claim can be made at .05 from this exact test with n=5; deterministic/fresh and single traces are excluded.')
    (ROOT/'results'/'main_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(valid_rows=len(raw),completed=sum(s['completed'] for s in status),seen=len(status))),flush=True)
if __name__=='__main__':run()

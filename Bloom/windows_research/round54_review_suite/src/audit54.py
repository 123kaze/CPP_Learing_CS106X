"""Four ledgers and predeclared dataset-cluster uncertainty; archive arithmetic only."""
import sys,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shared54 import *

def csvread(p):
    with p.open() as f:return list(csv.DictReader(f))

def writecsv(p,rows):
    with p.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
    check();start=time.perf_counter();r53=WR/'round53_index_free_recheck_v4/results';rows=[]
    budgets={'url':(64,128,256),'caida_flow':(16,24,32,256),'mawi2020_flow':(16,24,32,128),'mawi2021_flow':(16,24,32,128),'mawi2022_flow':(16,24,32,128),'mawi2024_flow':(16,24,32,128),'cod':(256,1024,4096),'caida':(128,256,1024,2048),'shalla':(256,1024,2048,4096)}
    for ds,ks in budgets.items():
        for kib in ks:
            w=json.loads((r53/f'{ds}_{kib}.json').read_text());assert w['status']=='complete'
            wl={a['workload']:a for a in w['workloads']}
            for r in w['rows']:
                q=wl[r['workload']];D=q['learning_state_bytes']//16
                rows.append(dict(dataset=ds,budget_kib=kib,workload=r['workload'],method=r['method'],deployment_M=kib*1024,deployment_used=r['total_bytes'],backend_index_required=0,prefix_counterfactual_index_bytes=8*w['members']+112,learning_count_payload=16*D,RA_rate_plus_count_payload=24*D,RA_rate_plus_count_with_headers=24*D+3*112,learning_trace_logical_bytes=q['learning_trace_bytes'],retained_full_trace_bytes=q['full_trace_bytes'],worker_shared_peak_RSS=w['peak_rss_bytes'],peak_scope='whole dataset-budget worker, not per-method isolated construction',raw_key_input_bytes=w['raw_key_blob_bytes']+w['raw_key_offsets_bytes'],selection_build_s=r['selection_build_s'],reference_replay_s=r['tail_reference_replay_s'],fp=r['fp'],member_fn=0))
    assert len(rows)==434;writecsv(ROOT/'results/four_ledgers.csv',rows)
    source=csvread(WR/'round19_gt_fix/results/updated_main_comparisons.csv')
    lens={}
    for p in sorted((WR/'round10_fpcache/results/main').glob('rows_*.csv')):
        for r in csvread(p):lens[(r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']))]=int(r['tail_len'])
    summaries={};detail=[]
    for fmt in ('index','fp64'):
        rr=[r for r in source if r['cohort']=='main' and r['cache']==fmt and r['workload']!='探测重放10%'];assert len(rr)==1076
        ds=sorted({r['dataset'] for r in rr});assert len(ds)==8
        for method,field in (('Gama','gama_fp'),('Replay','replay_fp'),('BF+Cache','bf_cache_fp')):
            records=[]
            for r in rr:
                key=(r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']));H=lens[key];a,b=int(r['repaired_ra_fp']),int(r[field])
                records.append(dict(dataset=key[0],budget_kib=key[1],workload=key[2],seed=key[3],cache=fmt,baseline=method,tail_queries=H,RA_fp=a,baseline_fp=b,absolute_delta=a-b,delta_per_million=(a-b)*1e6/H,smoothed_ratio=(a+1)/(b+1),low_FP_in_either=a<30 or b<30))
            detail+=records;cluster=[]
            for name in ds:
                a=[r for r in records if r['dataset']==name]
                cluster.append(dict(dataset=name,cases=len(a),mean_absolute_delta=float(np.mean([r['absolute_delta'] for r in a])),mean_delta_per_million=float(np.mean([r['delta_per_million'] for r in a])),mean_log_ratio=float(np.mean(np.log([r['smoothed_ratio'] for r in a])))))
            result=dict(cases=1076,wins=sum(r['absolute_delta']<0 for r in records),ties=sum(r['absolute_delta']==0 for r in records),losses=sum(r['absolute_delta']>0 for r in records),RA_FP_sum=sum(r['RA_fp'] for r in records),baseline_FP_sum=sum(r['baseline_fp'] for r in records),absolute_delta_quantiles=np.quantile([r['absolute_delta'] for r in records],[0,.25,.5,.75,1]).tolist(),low_FP_cases=sum(r['low_FP_in_either'] for r in records),clusters=cluster)
            for cohort,cs in (('all8',cluster),('original4flows',[c for c in cluster if c['dataset'].endswith('_flow')])):
                assert len(cs)==(8 if cohort=='all8' else 4)
                rng=np.random.default_rng(5401);ix=rng.integers(0,len(cs),(20000,len(cs)));boot={}
                for col in ('mean_absolute_delta','mean_delta_per_million','mean_log_ratio'):
                    v=np.array([c[col] for c in cs]);means=v[ix].mean(axis=1)
                    boot[col]=dict(equal_dataset_mean=float(v.mean()),CI95=np.quantile(means,[.025,.975]).tolist())
                result[cohort]=boot
            summaries[fmt+'/'+method]=result
    assert len(detail)==6456;writecsv(ROOT/'results/absolute1076.csv',detail)
    # Boundary fixture using exactly the frozen finite-window saturation branch.
    P=RA.ra4.Population(np.array([0]),np.array([.01]),np.array([2.]),np.array([0.]),np.array([100.]),np.array([1.]),100)
    e=np.array([.5]);assert np.array_equal(P.at_capacity(e,100)[0],P.Mg[-1]) and P.T[-1]==100000
    refs={str(p.relative_to(BLOOM)):sha(p) for p in (WR/'round17_zerotree/README.md',WR/'round20_zero_guard/README.md',BLOOM/'docs/review_evidence_20261123/gt19_14_cases.csv',BLOOM/'docs/review_evidence_20261123/theory_verification.json')}
    gt=csvread(BLOOM/'docs/review_evidence_20261123/gt19_14_cases.csv');assert len(gt)==28
    save(ROOT/'results/audit.json',dict(status='complete',ledger_rows=434,absolute_rows=6456,summary=summaries,GT19_case_keys=14,GT19_cache_rows=28,saturation=dict(T_grid_upper=100000,T_over_H=1000,returns_last_grid_mass=True),reused_evidence=refs,wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scope='Archive recomputation; no filter or timing rerun, no p-value retuning, percentile cluster intervals are descriptive with 8/4 clusters.'))
    print('AUDIT_COMPLETE 434 ledgers; 1076 cases per format',flush=True)

if __name__=='__main__':main()

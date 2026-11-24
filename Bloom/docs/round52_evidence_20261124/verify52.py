"""Read-only full-matrix audit; totals, worst cases and recipe-invariant baselines retained."""
from pathlib import Path
import json,csv,hashlib,statistics,time
BLOOM=Path(__file__).resolve().parents[2];ROOT=Path(__file__).resolve().parent;R=BLOOM/'windows_research/round52_sis_filter_controls'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    output=ROOT/'verification.json';assert not output.exists();started=time.perf_counter();freeze=json.loads((R/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in freeze[group].items():assert sha(BLOOM/p)==h,p
    methods=('Gama','Replay','RA-global','RA6-Exact128','BF+Exact128','PlainBF','ZGate-Exact128');groups={};worker_hashes={};model_grids=[]
    for recipe in ('original','balanced_clip'):
        for seed in (5001,5002,5003):
            p=R/f'results/{recipe}_{seed}.json';w=json.loads(p.read_text());worker_hashes[p.name]=sha(p);assert w['status']=='complete' and not w['pilot']
            assert len(w['rows'])==21 and len(w['controls'])==3 and w['members']==2749058
            model_grids.append(dict(recipe=recipe,seed=seed,actual_trees=w['actual_model_trees'],available=w['available_tree_prefixes']))
            ref50=json.loads((BLOOM/f'windows_research/round50_sis_fullfile_diagnostics/results/seed{seed}.json').read_text())
            ref51=json.loads((BLOOM/f'windows_research/round51_training_stability/results/seed{seed}.json').read_text());development=next(r for r in ref51['rows'] if r['recipe']==recipe)
            assert w['learning_sha256']==ref50['learning_sha256'] and w['tail_sha256']==ref50['tail_sha256'] and abs(w['development_auc16']-development['development_auc'])<1e-12
            for row in w['rows']:
                assert row['member_fn']==0 and row['required_extra_index_bytes']==0
                assert row['filter_bytes']==row['auxiliary_total_bytes']==sum(row[k] for k in ('model_payload_bytes','bf_payload_bytes','routing_bytes','header_bytes','cache_physical_bytes'))<=row['budget_kib']*1024
                key=(recipe,seed,row['budget_kib']);g=groups.setdefault(key,{})
                assert row['method'] not in g;g[row['method']]=row
            for c in w['controls']:
                assert not c['actual_CLOCK_fixed_T'] and {r['arm'] for r in c['rows']}=={'h','traffic','miss'}
                for row in c['rows']:assert row['member_BF_FN']==row['final_member_cache_hits']==0 and row['total_bytes']<=c['budget_kib']*1024
    expected={(r,s,b) for r in ('original','balanced_clip') for s in (5001,5002,5003) for b in (672,1343,2685)};assert set(groups)==expected
    for g in groups.values():
        assert set(g)==set(methods);z=g['ZGate-Exact128'];winner=g['BF+Exact128' if z['selection_info']['winner']=='BF' else 'RA6-Exact128']
        for f in ('fp','trees','cache_frac','filter_bytes','flags_sha256','cache_sha256'):assert z[f]==winner[f]
    for seed in (5001,5002,5003):
        for budget in (672,1343,2685):
            for method in ('BF+Exact128','PlainBF'):
                a,b=groups['original',seed,budget][method],groups['balanced_clip',seed,budget][method]
                for f in ('fp','trees','cache_frac','filter_bytes','flags_sha256','cache_sha256'):assert a[f]==b[f]
    pilot=json.loads((R/'results/pilot.json').read_text());assert pilot['status']=='complete'
    for r in pilot['rows']:
        formal=groups['balanced_clip',5001,r['budget_kib']][r['method']]
        for f in ('fp','trees','cache_frac','filter_bytes','flags_sha256','cache_sha256'):assert r[f]==formal[f]
    with (R/'results/main.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==126
    for r in rows:
        ref=groups[r['recipe'],int(r['seed']),int(r['budget_kib'])][r['method']]
        for k,v in ref.items():
            if not isinstance(v,(list,dict)):assert r[k]==str(v),k
    with (R/'results/controls.csv').open() as f:assert len(list(csv.DictReader(f)))==54
    summary=json.loads((R/'results/summary.json').read_text());details={}
    for recipe in ('original','balanced_clip'):
        gg={key:g for key,g in groups.items() if key[0]==recipe};totals={m:sum(g[m]['fp'] for g in gg.values()) for m in methods};comparisons={}
        for baseline in ('BF+Exact128','Replay','RA-global','Gama'):
            pp=[(g['RA6-Exact128']['fp'],g[baseline]['fp'],key) for key,g in gg.items()]
            calculated=dict(cases=len(pp),wins=sum(a<b for a,b,k in pp),ties=sum(a==b for a,b,k in pp),losses=sum(a>b for a,b,k in pp),median_smoothed_ratio=statistics.median((a+1)/(b+1) for a,b,k in pp))
            assert calculated==summary['comparisons'][recipe][baseline]
            worst=max(pp,key=lambda x:(x[0]+1)/(x[1]+1));comparisons[baseline]=dict(**calculated,worst=dict(seed=worst[2][1],budget_kib=worst[2][2],RA_FP=worst[0],baseline_FP=worst[1],smoothed_ratio=(worst[0]+1)/(worst[1]+1)))
        speed=[g['Replay']['selection_build_s']/(g['RA6-Exact128']['selection_build_s']+g['RA6-Exact128']['summary_charged_s']) for g in gg.values()]
        assert abs(1/statistics.median(speed)-summary['selection'][recipe]['median_RA_over_Replay'])<1e-12
        details[recipe]=dict(paired_comparisons=comparisons,matrix_FP_sums=totals,matrix_sum_not_a_single_deployment=True,median_paired_selection_speedup=statistics.median(speed),selection_wins=sum(x>1 for x in speed))
    result=dict(status='verified',main_rows=126,control_rows=54,case_keys=18,pilot_reproduced=True,identical_no_model_controls_between_recipes=True,all_member_FN=0,extra_member_index_bytes=0,details=details,actual_model_grids=model_grids,worker_sha256=worker_hashes,third_party_execution=False,new_independent_holdout=False,end_to_end_timing=False,seconds=time.perf_counter()-started,script_sha256=sha(Path(__file__)))
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(status='verified',details=details,main_rows=126,control_rows=54),indent=2))

if __name__=='__main__':main()

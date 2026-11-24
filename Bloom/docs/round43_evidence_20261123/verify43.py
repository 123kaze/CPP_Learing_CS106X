"""Independent arithmetic/coverage/hash audit; no experiment writes or SQL reruns."""
from pathlib import Path
import csv,json,hashlib,statistics,time,argparse
BLOOM=Path(__file__).resolve().parents[2];ROUND=BLOOM/'windows_research/round43_controlled_catalog'


def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main(output,inputs):
    assert not output.exists();start=time.perf_counter();freeze=json.loads((ROUND/'plan/freeze.json').read_text());missing=[]
    for p,h in freeze['sources'].items():
        if not (BLOOM/p).exists():missing.append(p)
        else:assert digest(BLOOM/p)==h,p
    cases={};allrows=[];sources={}
    for a in (0,6):
        for seed in (4301,4302,4303):
            p=ROUND/f'results/a{a}_s{seed}.json';w=json.loads(p.read_text());sources[str(p.relative_to(BLOOM))]=digest(p)
            assert w['status']=='complete' and not w['pilot'] and (w['strength'],w['seed'])==(a,seed)
            assert w['catalogue']['members']==65536 and w['catalogue']['query_negative_keys']==65536 and len(w['cases'])==9
            if inputs:
                p=ROUND/f'cache/a{a}_s{seed}.npz';assert digest(p)==w['local_generated_input_sha256']
            for c in w['cases']:
                key=(a,seed,c['association'],c['budget_kib']);assert key not in cases
                cases[key]=c;assert c['learning_queries']==250000 and c['tail_queries']==750000
                rr={r['method']:r for r in c['rows']};assert set(rr)=={'Gama','Replay','RA-global','RA6','BF+Cache','PlainBF','ZGate'}
                for r in rr.values():
                    assert r['member_fn']==0 and r['required_backend_index_bytes']==0
                    assert sum(r[k] for k in ('model_bytes','bf_bytes','routing_bytes','headers','cache_bytes'))==r['total_bytes']<=c['budget_kib']*1024
                    allrows.append(dict(strength=a,seed=seed,association=c['association'],budget_kib=c['budget_kib'],**r))
                winner=c['selection']['zgate_winner'];z=rr['ZGate'];ref=rr[winner]
                for field in ('fp','trees','cache_frac','total_bytes','cache_sha256','static_flags_sha256'):assert z[field]==ref[field]
                ctrl=c['controls'];assert ctrl['status']=='complete' and not ctrl['actual_clock_fixed_T']
                assert {r['arm'] for r in ctrl['rows']}=={'h','traffic','miss'}
                for r in ctrl['rows']:assert r['total_bytes']<=c['budget_kib']*1024 and r['member_fn']==0
                timing={(r['member_target'],r['method'],r['rep']):r for r in c['timings']};assert len(timing)==24
                for pvalue in (.1,.9):
                    for method in ('NoFilter','BF+Cache','RA6','Replay'):
                        t=[timing[pvalue,method,i] for i in range(3)]
                        assert len({r['accepted_sha256'] for r in t})==len({r['cache_sha256'] for r in t})==1
                        assert all(r['reference_equal'] and r['member_fn']==0 and r['queries']==20000 and r['backend_calls']==r['fp']+r['members_found'] and r['members_found']==r['actual_members'] for r in t)
                    assert len({r['request_sha256'] for r in c['timings'] if r['member_target']==pvalue})==1
                if inputs:
                    p=ROUND/f'cache/a{a}_s{seed}_{c["association"]}.npz';assert digest(p)==c['stream']['local_stream_file_sha256']
    expected={(a,s,c,b) for a in (0,6) for s in (4301,4302,4303) for c in ('neutral','high_hot','low_hot') for b in (16,32,64)};assert set(cases)==expected
    # CSV tables independently checked against original JSON or exact paired arithmetic.
    with (ROUND/'results/main.csv').open() as f:csvrows=list(csv.DictReader(f))
    assert len(csvrows)==378
    expected_rows={(r['strength'],r['seed'],r['association'],r['budget_kib'],r['method']):r for r in allrows}
    for r in csvrows:
        ref=expected_rows[int(r['strength']),int(r['seed']),r['association'],int(r['budget_kib']),r['method']]
        assert all(str(v)==r[k] for k,v in ref.items())
    with (ROUND/'results/cost_crossovers.csv').open() as f:cost=list(csv.DictReader(f))
    assert len(cost)==324
    for row in cost:
        c=cases[int(row['strength']),int(row['seed']),row['association'],int(row['budget_kib'])];p=float(row['member_target']);b=row['baseline']
        a=[next(r for r in c['timings'] if r['member_target']==p and r['method']=='RA6' and r['rep']==i) for i in range(3)]
        bb=[next(r for r in c['timings'] if r['member_target']==p and r['method']==b and r['rep']==i) for i in range(3)]
        saved=bb[0]['backend_calls']-a[0]['backend_calls'];delta=statistics.median(x['elapsed_ns']-y['elapsed_ns'] for x,y in zip(a,bb))
        assert int(row['backend_calls_saved'])==saved and abs(float(row['measured_window_delta_s'])-delta/1e9)<1e-12
        if saved>0:assert abs(float(row['additional_backend_us_for_query_crossover'])-max(0,delta/1000/saved))<1e-9
        else:assert row['additional_backend_us_for_query_crossover']==''
    for name,n in [('controls.csv',162),('timings.csv',1296),('cost_projections.csv',1296),('diagnostics.csv',54)]:
        with (ROUND/'results'/name).open() as f:assert len(list(csv.DictReader(f)))==n
    receipt=dict(status='verified' if not missing else 'partial_sources_missing',case_keys=54,main_rows=378,control_rows=162,query_timings=1296,source_hashes_checked=len(freeze['sources'])-len(missing),missing_sources=missing,generated_inputs_checked=inputs,SQL_rerun=False,third_party_execution=False,source_worker_hashes=sources,seconds=time.perf_counter()-start,verifier_sha256=digest(Path(__file__)))
    with output.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--inputs',action='store_true');a=p.parse_args();main(a.output,a.inputs)

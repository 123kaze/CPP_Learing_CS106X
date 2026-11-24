"""Read-only independent coverage, prefix-label, split and archive checks."""
from pathlib import Path
import sys,json,csv,hashlib,statistics,time,argparse
BLOOM=Path(__file__).resolve().parents[2];ROOT=BLOOM/'windows_research/round44_trace_snapshot';REPORT=ROOT.parent/'round44_report_v2'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main(output,inputs):
    assert not output.exists();start=time.perf_counter();freeze=json.loads((ROOT/'plan/freeze.json').read_text());missing=[]
    for rel,h in freeze['sources'].items():
        if (BLOOM/rel).exists():assert sha(BLOOM/rel)==h,rel
        else:missing.append(rel)
    if inputs:
        for rel,h in freeze['inputs'].items():assert sha(BLOOM/rel)==h,rel
    v2freeze=json.loads((REPORT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for rel,h in v2freeze[group].items():assert sha(BLOOM/rel)==h,rel
    summary=json.loads((REPORT/'results/summary.json').read_text());assert summary['status']=='verified' and not summary['original_production_NotFound_evidence']
    assert json.loads((ROOT/'results/failure.json').read_text())['status']=='failed'
    expected={};catalog_checks=[];source_hashes={}
    for cluster in ('cluster001','cluster002','cluster003'):
        q=json.loads((ROOT/f'results/{cluster}_qualification.json').read_text());m=json.loads((ROOT/f'results/{cluster}_data.json').read_text())
        assert not m['member_catalog_uses_future'] and not m['original_backend_NotFound_inferred'];assert q['method_FP_not_measured']
        assert len(q['diagnostics'])==3
        if inputs:
            import numpy as np
            p=ROOT/f'cache/{cluster}.npz';assert sha(p)==m['prepared_sha256']
            with np.load(p,allow_pickle=False) as d:ids,y,first,trace,ce,le,blob,off=[d[k] for k in ('ids','y','first','trace','catalog_end','learn_end','blob','offsets')]
            ce,le=int(ce),int(le);assert ce==len(trace)//4 and le==len(trace)//2
            actual=np.zeros(len(ids),np.bool_);actual[np.unique(trace[:ce])]=True;assert np.array_equal(actual,y) and int(y.sum())==m['members']
            assert np.array_equal(y,first<ce) and len(np.unique(ids))==len(ids)
            for i,ident in enumerate(ids):assert int.from_bytes(hashlib.sha256(blob[off[i]:off[i+1]].tobytes()).digest()[:8],'little')==int(ident)
            catalog_checks.append(dict(cluster=cluster,members=int(y.sum()),key_identity_verified=True,member_set_exactly_first_quarter_GETs=True,future_used=False))
        if not q['eligible_for_method_comparison']:continue
        budgets=sorted({max(4,(m['members']*bits+8191)//8192) for bits in (2,4,8)})
        for seed in (4401,4402,4403):
            p=ROOT/f'results/{cluster}_{seed}.json';w=json.loads(p.read_text());assert w['status']=='complete' and len(w['rows'])==len(budgets)*7;source_hashes[str(p.relative_to(ROOT))]=sha(p)
            d=next(r for r in q['diagnostics'] if r['seed']==seed)
            assert w['learning_sha256']==d['learning_sha256'] and w['tail_sha256']==d['tail_sha256']
            for r in w['rows']:
                key=(cluster,seed,r['budget_kib'],r['method']);assert key not in expected and r['budget_kib'] in budgets
                assert r['filter_bytes']==sum(r[k] for k in ('model_payload_bytes','bf_payload_bytes','routing_bytes','header_bytes','cache_physical_bytes'))
                assert r['required_extra_index_bytes']==0 and r['filter_bytes']==r['auxiliary_total_bytes']<=r['budget_kib']*1024
                assert r['member_fn']==r['final_member_cache_hits']==0 and r['mixed_backend_calls']==r['fp']+w['tail_mixed_members']
                expected[key]=r
            for budget in budgets:
                group={r['method']:r for r in w['rows'] if r['budget_kib']==budget};assert set(group)=={'Gama','Replay','RA-global','RA6-Exact128','BF+Exact128','PlainBF','ZGate-Exact128'}
                z=group['ZGate-Exact128'];winner=group['BF+Exact128' if z['selection_info']['winner']=='BF' else 'RA6-Exact128']
                for f in ('fp','trees','cache_frac','cache_sha256','flags_sha256','filter_bytes'):assert z[f]==winner[f]
    with (REPORT/'results/main.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(expected)==summary['main_rows']
    for row in rows:
        ref=expected[row['cluster'],int(row['seed']),int(row['budget_kib']),row['method']]
        for key,value in ref.items():
            if not isinstance(value,(list,dict)):assert row[key]==str(value),key
    for cluster,comparisons in summary['comparisons'].items():
        for baseline,reported in comparisons.items():
            keys=[k for k in expected if k[0]==cluster and k[-1]=='RA6-Exact128']
            pairs=[(expected[k]['fp'],expected[(*k[:3],baseline)]['fp']) for k in keys]
            assert len(pairs)==reported['cases'] and sum(a<b for a,b in pairs)==reported['wins'] and sum(a==b for a,b in pairs)==reported['ties'] and sum(a>b for a,b in pairs)==reported['losses']
            assert abs(statistics.median((a+1)/(b+1) for a,b in pairs)-reported['median_smoothed_ratio'])<1e-12
    result=dict(status='verified' if not missing else 'partial_sources_missing',main_rows=len(rows),all3candidates_accounted=True,missing_sources=missing,inputs_checked=inputs,catalog_checks=catalog_checks,worker_hashes=source_hashes,original_reporting_failure_retained=True,report_v2_checked=True,original_production_NotFound_evidence=False,third_party_execution=False,seconds=time.perf_counter()-start,verifier_sha256=sha(Path(__file__)))
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output,a.inputs)

"""Independent arithmetic/hash checks; no experiments or downloads rerun."""
from pathlib import Path
import json,hashlib,statistics,time
BLOOM=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;WR=BLOOM/'windows_research'

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    target=HERE/'verification.json';assert not target.exists();start=time.perf_counter();counts={}
    for name in ('round45_namespace_diagnostics','round46_dns_qualification','round46_dns_qualification_v2'):
        r=WR/name;freeze=json.loads((r/'plan/freeze.json').read_text())
        for group in ('sources','inputs'):
            for p,h in freeze.get(group,{}).items():assert sha(BLOOM/p)==h,(name,p)
        counts[name]=dict(sources=len(freeze['sources']),inputs=len(freeze.get('inputs',{})))
    r=WR/'round45_namespace_diagnostics';result=json.loads((r/'results/verification.json').read_text());passed=0;models=0
    for cluster in ('cluster001','cluster002','cluster003'):
        w=json.loads((r/f'results/{cluster}.json').read_text());assert w['status']=='complete';models+=len(w['rows']);lookup={(x['seed'],x['representation']):x for x in w['rows']}
        old=json.loads((WR/f'round44_trace_snapshot/results/{cluster}_qualification.json').read_text())
        for seed in (4401,4402,4403):
            ref=next(x for x in old['diagnostics'] if x['seed']==seed)
            assert abs(lookup[seed,'lexical24']['development_auc']-ref['development_auc16'])<1e-12
            for rep in ('prefix88','combined89'):assert lookup[seed,rep]['vocab_allocated_bytes']==448 and lookup[seed,rep]['vocab_payload_bytes']==336
        gain=statistics.median(lookup[s,'combined89']['development_auc']-lookup[s,'lexical24']['development_auc'] for s in (4401,4402,4403));auc=statistics.median(lookup[s,'combined89']['development_auc'] for s in (4401,4402,4403))
        good=gain>=.03 and auc>=.65;passed+=good;g=next(g for g in result['groups'] if g['cluster']==cluster)
        assert abs(g['median_paired_combined_gain']-gain)<1e-12 and g['passes_development_gate']==good
    assert models==36 and passed==0 and result['advance_to_unseen_clusters']==(passed>=2) and not result['new_clusters_opened']
    old=WR/'round46_dns_qualification';v2=WR/'round46_dns_qualification_v2';d=json.loads((old/'results/download.json').read_text());schema=json.loads((v2/'results/schema_verification.json').read_text());meta=json.loads((v2/'results/data.json').read_text());q=json.loads((v2/'results/qualification.json').read_text())
    assert d['status']=='verified' and d['uncompressed_sha256']==schema['original_body_sha256'] and d['uncompressed_bytes']==schema['original_body_bytes']==62075487
    assert schema['records']==meta['records']==427935 and sum(meta['rcode_counts'].values())==meta['A_queries']==212477
    assert meta['all_A_NXDOMAIN_requests']==meta['rcode_counts']['3']==21825 and meta['retained_NXDOMAIN_requests']==21733
    assert abs(meta['retained_NXDOMAIN_fraction']-21733/21825)<1e-12
    assert meta['members']==18 and meta['negative_keys']==1045 and not q['eligible_for_methods'] and q['reasons']==['members<1000']
    assert json.loads((old/'results/failure.json').read_text())['error']=='MissingZeek#fields'
    receipt=dict(status='verified',source_input_counts=counts,development_models=36,old_auc_regressions=9,development_gate_passed_clusters=0,new_Twitter_holdout_opened=False,DNS_records=427935,DNS_members=18,DNS_eligible=False,original_schema_failure_preserved=True,no_new_positive_method_result=True,seconds=time.perf_counter()-start,script_sha256=sha(Path(__file__)))
    with target.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()

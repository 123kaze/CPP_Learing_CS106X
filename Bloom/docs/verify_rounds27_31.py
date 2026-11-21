"""Read-only, stdlib-only verification of published rounds27--31 (no datasets or reruns)."""
from pathlib import Path
import hashlib,json,math,csv
ROOT=Path(__file__).resolve().parents[1]
NAMES=('round27_http_real','round28_reweight_mechanism','round29_evidence_audit','round29_evidence_audit_v2','round30_submission_audit','round31_sqlite_online')
REPORT17='windows_research/round17_zerotree/src/report17.py'
ORIGINAL='16eb59c0fdee76de34de9c228a3dca91aa60e040c6bff490f7135506b2bd3645'
PUBLISHED='d02a45966a478fc00b6e880205b24e5a2eee6c2323cfa5a0b5ca1ef8cfaf0c09'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())


def main():
    exceptions=[]
    for name in NAMES:
        root=ROOT/'windows_research'/name;freeze=load(root/'plan/freeze.json')
        for rel,expected in freeze.get('sources',freeze.get('sources_and_inputs',{})).items():
            actual=sha(ROOT/rel)
            if actual!=expected:
                assert name in ('round29_evidence_audit','round29_evidence_audit_v2') and rel==REPORT17 and expected==ORIGINAL and actual==PUBLISHED,(name,rel,'Unexpected source change')
                exceptions.append(name+': exact report-only historical prose variant accepted')
        archive=load(root/'archive_manifest.json')
        for rel,h in archive['files'].items():assert sha(root/rel)==h,(name,rel,'Archive changed')
        if name=='round29_evidence_audit':
            assert archive['status']=='failed_preserved' and not (root/'results/completion.json').exists()
        else:assert archive['status']=='complete' and load(root/'results/completion.json')['status']=='complete'
    r27=ROOT/'windows_research/round27_http_real/results';total=0
    for ds in ('nasa_jul95','nasa_aug95'):
        for seed in (2701,2702,2703):
            d=load(r27/f'{ds}_{seed}.json');assert d['status']=='complete' and len(d['rows'])==15
            for r in d['rows']:
                assert r['member_fn']==0 and r['processed']==d['tail_queries'] and r['total_bytes']<=r['budget_kib']*1024
                assert sum(r[k] for k in ('model_payload_bytes','bf_payload_bytes','metadata_bytes','array_overhead_bytes','cache_physical_bytes'))==r['total_bytes']
                total+=1
    assert total==90
    r28=ROOT/'windows_research/round28_reweight_mechanism/results';cases=builds=0
    for ds in ('url','caida_tcp_flow'):
        d=load(r28/f'{ds}.json');assert d['status']=='complete' and len(d['cases'])==84
        for r in d['cases']:
            cases+=1
            for family in ('paper_identity','exact_identity'):
                z=r[family];active=[i for i,p in enumerate(z['p']) if p>0];u=[z['M'][i]/z['h'][i] for i in active]
                factor=sum(z['p'][i]*v for i,v in zip(active,u))/math.exp(sum(z['p'][i]*math.log(v) for i,v in zip(active,u)))
                assert math.isclose(factor,z['arithmetic_geometric_factor'],rel_tol=1e-9)
                if z['interior']:assert math.isclose(z['conditional_baseline_fp']/z['conditional_reweighted_fp'],factor,rel_tol=1e-9)
            for a in r['arms'].values():
                builds+=1;assert a['member_fn']==0 and a['used_bits']<=r['budget_bits'] and a['clock']['processed']==300000
    assert (cases,builds)==(168,504)
    r29=ROOT/'windows_research/round29_evidence_audit_v2/results';d=load(r29/'summary.json')
    assert d['resource_rows']==60 and d['zero_tree']['cases']==192 and d['zero_tree']['tail_regressions_vs_RA6']==26
    s=d['statistics']['index/repaired_ra_fp'];assert s['original_cluster_count']==21 and s['datasets']==8
    assert s['dataset_cluster_percentile95'][0]<1<s['dataset_cluster_percentile95'][1]
    with (r29/'resources.csv').open() as f:
        for r in csv.DictReader(f):assert sum(int(r[k]) for k in ('model_bytes','bf_bytes','metadata_bytes','overhead_bytes','cache_alloc_bytes'))==int(r['total_bytes'])<=int(r['budget_kib'])*1024
    r30=ROOT/'windows_research/round30_submission_audit/results';d=load(r30/'numeric_audit.json')
    assert sum(r['nonworse'] for r in d['sensitivity'])==13 and math.isclose(d['gt_example']['total'],4/3)
    search=load(r30/'no_repeat_search.json');assert search['status']=='none_found_in_prespecified18settings' and len(search['searched'])==18
    r31=ROOT/'windows_research/round31_sqlite_online/results';total=0
    for ds in ('cod','url','caida','shalla','caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow'):
        d=load(r31/f'{ds}.json');assert d['status']=='complete';total+=len(d['timings'])
        for r in d['timings']:
            assert r['member_fn']==0 and r['full_mask_equal_reference'] and r['packed_cache_equal_reference']
            assert r['backend_calls']==r['fp']+r['members_found'] and r['members_found']==d['member_queries']
            if r['method']!='NoFilter':
                expected=d['methods'][r['method']]
                assert r['accepted_mask_sha256']==expected['expected_mask_sha256'] and r['final_cache_sha256']==expected['expected_cache_sha256']
    assert total==312
    print('PASS: HTTP90; mechanism168pairs/504builds; resources60; no-repeat18; SQLite312; failed round29 preserved')
    for message in exceptions:print('EXPLICIT COMPATIBILITY:',message)
    print('No raw data, manuscript editing, training or experiment execution performed.')


if __name__=='__main__':main()

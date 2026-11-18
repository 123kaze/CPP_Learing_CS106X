"""Complete-results report; old tables stay immutable, revised aggregates separate."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
DATASETS=('caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow','mawi2024_flow','cod','url','caida','shalla')


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def stat(rows,column,reference):
    values=[(r[column]+1)/(r[reference]+1) for r in rows]
    return dict(cases=len(rows),median=median(values),wins=sum(r[column]<r[reference] for r in rows),
                ties=sum(r[column]==r[reference] for r in rows),losses=sum(r[column]>r[reference] for r in rows))


def collect(root=ROOT,with_inputs=False):
    assert __debug__,'Assertions required'
    bloom=root.parents[1];wr=root.parent;seen={}
    def load(p):
        seen[str(p.relative_to(bloom))]=digest(p)
        return json.loads(p.read_text())
    manifest=load(root/'results/manifest.json');freeze=load(root/'plan/freeze.json')
    assert manifest['freeze']==freeze
    for rel,h in freeze['sources'].items():assert digest(bloom/rel)==h,rel
    if with_inputs:
        for rel,h in freeze['inputs'].items():assert digest(bloom/rel)==h,rel
    done=load(root/'results/completion.json');audit=load(root/'results/audit_completion.json')
    assert done['status']=='complete' and not done['changed_extras'],'Additional affected inputs unresolved'
    assert done['cache_specific_rechecks']==28 and done['main_statistics_unchanged']==1132
    assert done['manifest_sha256']==digest(root/'results/manifest.json')
    audits=[]
    for ds in DATASETS:
        r=load(root/f'results/audit_{ds}.json');assert r['status']=='complete' and r['exit_code']==0
        for row in r['streams']:
            if row['rate_bit_equal']:assert row['original_rate_sha256']==row['repaired_rate_sha256'] and row['changed_keys']==0
            else:assert row['changed_keys']>0 and row['repair_bins']
            audits.append(row)
    assert len(audits)==325
    main=[r for r in audits if r['cohort']=='main'];hold=[r for r in audits if r['cohort']=='holdout']
    assert sum(len(r['budgets']) for r in main)==1146
    assert sum(len(r['budgets']) for r in main if r['rate_bit_equal'])==1132
    assert sum(len(r['budgets']) for r in hold if r['rate_bit_equal'])==4
    extras=load(root/'results/audit_extras.json');assert extras['status']=='complete' and extras['exit_code']==0
    assert not extras['changed'] and all(r['rate_bit_equal'] and r['changed_keys']==0 for r in extras['streams'])
    assert audit['extra_inputs']==len(extras['streams'])
    affected=json.loads((wr/'round18_gt_audit/results/affected_cases.json').read_text())
    expected={(r['dataset'],r['budget_kib'],r['workload'],r['seed'],mode) for r in affected for mode in ('index','fp64')}
    cases=[];rows=[]
    for ds in ('cod','url','caida','shalla'):
        for mode in ('index','fp64'):
            r=load(root/f'results/rerun_{ds}_{mode}.json');assert r['status']=='complete' and r['exit_code']==0
            for c in r['cases']:
                assert (c['dataset'],c['cache'])==(ds,mode)
                expected_methods={'RA6'} if mode=='fp64' else {'RA6','RA6-top3','RA6-top10','RA4','RA4-noRepeat','RA4-noSA','RA4-noGT','RA4-mix0.5','RA4-mix1','RA4-Table','RA-global'}
                assert set(c['methods'])==expected_methods
                for method,m in c['methods'].items():
                    a,b=m['old'],m['repaired'];assert m['old_matches_archive']
                    assert m['same_fp']==(a['fp']==b['fp'])
                    assert m['identical_payload']==(a['payload_sha256']==b['payload_sha256'])
                    assert m['identical_static_flags']==(a['static_flags_sha256']==b['static_flags_sha256'])
                    assert m['same_configuration']==all(a[k]==b[k] for k in ('trees','frac','cache_bytes','total_bytes'))
                    for v in (a,b):assert type(v['fp']) is int and v['fp']>=0 and v['total_bytes']<=c['budget_kib']*1024 and math.isfinite(v['predicted_fp'])
                    if method=='RA4-noGT':assert m['same_configuration'] and m['identical_payload'] and m['same_fp'] and a['predicted_fp']==b['predicted_fp']
                    rows.append(dict(dataset=ds,cache=mode,budget_kib=c['budget_kib'],workload=c['workload'],seed=c['seed'],method=method,
                                     old_fp=a['fp'],repaired_fp=b['fp'],old_trees=a['trees'],repaired_trees=b['trees'],
                                     old_frac=a['frac'],repaired_frac=b['frac'],old_prediction=a['predicted_fp'],repaired_prediction=b['predicted_fp'],
                                     same_configuration=m['same_configuration'],identical_payload=m['identical_payload'],same_fp=m['same_fp']))
                if mode=='index':
                    assert c['warm']['same_fp']==(c['warm']['old_fp']==c['warm']['repaired_fp'])
                    assert c['candidate_changes']
                    for x in c['candidate_changes']:
                        if x['identical_static_flags_and_cache']:
                            assert x['old_fp']==x['repaired_fp'] and x['repaired_fp_source'].startswith('archived value')
                        else:assert x['repaired_fp_source']=='new frozen tail replay'
                cases.append(c)
    assert len(cases)==28 and {(c['dataset'],c['budget_kib'],c['workload'],c['seed'],c['cache']) for c in cases}==expected
    refpath=wr/'round13_complete/results/combined_baseline_rows.csv';assert digest(refpath)==freeze['inputs'][str(refpath.relative_to(bloom))]
    with refpath.open() as f:base=list(csv.DictReader(f))
    changed={(c['dataset'],c['budget_kib'],c['workload'],c['seed'],c['cache']):c['methods']['RA6'] for c in cases}
    full=[]
    for r in base:
        key=(r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']),r['cache'])
        repair=changed.get(key);old=int(r['ra_fp'])
        if repair:assert repair['old']['fp']==old
        full.append(dict(dataset=r['dataset'],budget_kib=int(r['budget_kib']),workload=r['workload'],seed=int(r['seed']),cache=r['cache'],
                         cohort=r['cohort'],included=r['included']=='True',old_ra_fp=old,repaired_ra_fp=repair['repaired']['fp'] if repair else old,
                         bf_cache_fp=int(r['bfcache_fp']),gama_fp=int(r['gama_fp']),replay_fp=int(r['replay_fp']),reference_fp=float(r['reference_fp']),
                         provenance='affected-case recomputation' if repair else 'unchanged-input archive; not a fresh filter execution'))
    summary={}
    for mode in ('index','fp64'):
        rr=[r for r in full if r['cache']==mode and r['cohort']=='main' and r['workload']!='探测重放10%' and r['included']]
        assert len(rr)==748
        for ref in ('bf_cache_fp','gama_fp','replay_fp','reference_fp'):
            summary[f'{mode}/{ref}']=dict(old=stat(rr,'old_ra_fp',ref),repaired=stat(rr,'repaired_ra_fp',ref))
    changes=dict(selected_method_comparisons=len(rows),selected_fp_changes=sum(not r['same_fp'] for r in rows),
                 selected_configuration_changes=sum(not r['same_configuration'] for r in rows),
                 selected_payload_changes=sum(not r['identical_payload'] for r in rows),
                 selected_prediction_changes=sum(r['old_prediction']!=r['repaired_prediction'] for r in rows),
                 warm_fp_changes=sum(not c['warm']['same_fp'] for c in cases if 'warm'in c),
                 candidate_records=sum(len(c['candidate_changes']) for c in cases),
                 candidate_fp_changes=sum(x['old_fp']!=x['repaired_fp'] for c in cases for x in c['candidate_changes']),
                 candidate_prediction_changes=sum(x['old_pred']!=x['repaired_pred'] or x['old_bucket_pred']!=x['repaired_bucket_pred'] for c in cases for x in c['candidate_changes']),
                 rank_top10_changes=sum(c.get('rank_old_top10')!=c.get('rank_repaired_top10') for c in cases if 'rank_old_top10' in c))
    return cases,rows,full,summary,changes,dict(status='verified',actual_main_statistic_cases=1146,unchanged=1132,
             affected_cases=14,cache_specific_rechecks=28,unchanged_holdout=4,unchanged_extra_inputs=len(extras['streams']),
             checked_raw_inputs=with_inputs,records=seen)


def render(cases,rows,full,summary,changes,verification):
    lines=['# Repeated-frequency-gap repair: verified impact','',
           'New round19 repair:retain c only for gt=True,2<=c<=5 and empty N[c+1]. Singleton, counts above5 and gt=False remain byte-identical. '
           'This is a post-freeze local repair, not SGT, normalization, a new zero-tree rule or an unbiasedness/optimality claim.','',
           f"Actual inputs:all1146 main cases checked;1132 unchanged statistic arrays,14 changed cases. All4 MAWI-24 budgets unchanged. Expanded audit:{verification['unchanged_extra_inputs']} actual supplementary learning inputs unchanged.",
           '', '## Old versus repaired main summaries (original748 eligible cases per format)','',
           '| Cache | Reference | Old median | Repaired median | Old win/tie/loss | Repaired win/tie/loss |',
           '|---|---|---:|---:|---|---|']
    for key,s in summary.items():
        a,b=s['old'],s['repaired'];cache,ref=key.split('/')
        lines.append(f"| {cache} | {ref} | {a['median']:.9g} | {b['median']:.9g} | {a['wins']}/{a['ties']}/{a['losses']} | {b['wins']}/{b['ties']}/{b['losses']} |")
    lines+=['','## Changes in all affected RA-family checks','']
    lines += [f'- {k}: {v}' for k,v in changes.items()]
    lines+=['','## Affected-case selected results','',
            '| Dataset | KiB | Seed | Cache | Method | Old FP | Repaired FP | Same configuration | Identical BF payload |',
            '|---|---:|---:|---|---|---:|---:|---|---|']
    for r in rows:
        lines.append(f"| {r['dataset']} | {r['budget_kib']} | {r['seed']} | {r['cache']} | {r['method']} | {r['old_fp']} | {r['repaired_fp']} | {r['same_configuration']} | {r['identical_payload']} |")
    lines+=['','## Verification and limits','',
            '- reference_fp is the original eligibility/Hindsight-or-Replay reference. For fp64 it retains the old indexed reference and is a legacy diagnostic, NOT a same-format comparator; use replay_fp for the same-format Replay comparison. Original cluster-significance tests and all paper tables have not been recomputed by this report.',
            '- The runtime hook is restored on success/error and frozen source hashes are checked. A new adapter owns outputs and distinguishes old-archive reproduction from repaired results; old files are never overwritten and stale old-result assertions are not used to force repaired equality.',
            '- All selected affected structures are actually evaluated on the original tails and compared by configuration, reconstructed packed BF payload and full-pool flags. Warm-cache results, all indexed GT ablations, top3/5/10 and fp64 RA6 are included.',
            '- E3 candidates with identical full-pool flags and cache bytes on the same stream reuse archived FP counts with an explicit deterministic-equivalence justification. Candidates whose flags change undergo new tail replay. Prediction and rank changes are retained separately from unchanged winner FP; “all results unchanged” is not inferred just from equal main totals.',
            '- Unaffected rows retain archive provenance, justified by byte-identical statistic fields and unchanged remaining inputs/code. They are not relabeled as1132 newly executed filters. Original holdout records remain frozen; no revised holdout has been substituted.',
            '- Supplemental coverage includes E10 learning shares, E11 learning prefixes, paper-source once/Zipf, old E5 scaling, round7/14 compressed inputs, round15 up to100M and TCP-only. E4/e789 use the covered main25% prefixes; round12 cost aggregation does not itself execute the counter.',
            '- This patch prevents the missing-next-bin repeated-count collapse only. Boundary discontinuity, nonmonotone adjusted counts, singleton uncertainty and non-unit total mass remain. It is not proof that this estimator is best among SGT/parametric/nonparametric alternatives.',
            '- Existing timing figures describe the original frozen implementation. No new speedup measurement is claimed here; diagnostic rerun wall times are not interchangeable with the original timing protocol.',
            '- The external estimator-comparison script reported at /tmp/est_cmp.py was absent on this machine. Its results and citation-based claims of finite-sample unbiasedness or optimality are not independently verified and not adopted.',
            '- This repair bundle does not restore deleted round16 publication files. Paper/formula changes remain a separate authorized action.']
    outputs={'report.md':'\n'.join(lines)+'\n','summary.json':json.dumps(dict(main=summary,changes=changes),indent=2)+'\n'}
    for name,data in (('selected_comparisons.csv',rows),('updated_main_comparisons.csv',full)):
        b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=list(data[0]));w.writeheader();w.writerows(data);outputs[name]=b.getvalue()
    return outputs


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    results=collect(with_inputs=a.inputs)
    for name,text in render(*results).items():
        out=ROOT/'results'/name
        if a.verify_only:assert out.read_bytes()==text.encode(),name
        else:out.write_bytes(text.encode())
    if not a.verify_only:(ROOT/'results/verification.json').write_text(json.dumps(results[-1],indent=2)+'\n')
    print('PASS: actual-input invariance,28 affected rechecks,RA-family/candidate comparisons and main summary arithmetic')

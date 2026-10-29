"""Verify raw results, frozen code, source workbook and protected directories."""
import json,hashlib,sys,time
from pathlib import Path
import numpy as np
import engine as E
ROOT=E.ROOT
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
def verify():
    checks=[];counts={}
    assert (ROOT/'results'/'EXPERIMENTS_COMPLETE.json').exists()
    raw=[]
    for ds,budgets in E.BUDGETS.items():
        for kib in budgets:
            p=ROOT/'results'/'main'/ds/f'{kib}.json';o=read(p);assert o['completed']
            keys=[(r['workload'],r['seed'],r['method']) for r in o['rows']];assert len(keys)==len(set(keys))
            for r in o['rows']:
                assert r['actual_filter_state_bytes']<=kib*1024 and r['member_false_negatives']==0
                assert r['sketch_deployed_bytes']==0 and r['cold_suffix']
                assert r['actual_filter_state_bytes']==sum(r[x] for x in ('model_bytes','bf_bytes','metadata_bytes','array_overhead_bytes','cache_allocated_bytes'))
                assert r['cache_returned_bytes']==r['cache_reserved_bytes']-r['cache_allocated_bytes']>=0
                assert r['fpr']==r['fp_tail']/r['evaluation_queries']
                assert r['evaluation_queries']+r['learning_queries']==r['queries']
                if not ds.endswith('_flow') and r['workload'] not in ('全新对抗','每key一次'):assert r['queries']==10000000
            methods={r['method'] for r in o['rows']}
            expected={'Gama','StreamModel','LearnGrid','BFCacheGrid','SkiQFAdmission2'}
            if not ds.endswith('_flow'):expected.add('Fixed48Grid')
            assert methods==expected,(ds,kib,methods)
            raw+=o['rows']
    counts['primary_rows']=len(raw);assert len(raw)==5685
    checks.append('20 main dataset/budget settings complete: 10M repeated workloads, paired seeds, cold suffixes, component byte sums, no false negatives')
    for ds in E.BUDGETS:
        s,_,safe=E.load(ds)
        assert len(np.unique(s.ids))==len(s.ids),'Observed original-ID/prehash collision invalidates exact-key replay assumption'
        sp=s.split
        assert not np.any((sp['member_train']|sp['neg_train'])&sp['neg_val'])
        assert not np.any((sp['member_train']|sp['neg_train']|sp['neg_val'])&sp['neg_test'])
        if ds.endswith('_flow'):
            with np.load(ROOT/'cache'/ds/'data.npz') as a:assert list(a['features'])==['src','dst']
        E.R._GSETUPS.clear()
    checks.append('All seven dataset splits disjoint; all three real-trace models use addresses only')
    from check_model_scores import check as check_scores
    if not (ROOT/'evidence'/'score-agreement'/'mawi2022_flow.json').exists():check_scores('mawi2022_flow')
    for ds in E.BUDGETS:assert read(ROOT/'evidence'/'score-agreement'/f'{ds}.json')['status']=='passed'
    checks.append('All14 saved model prefixes agree with cached scores on >=5000 deterministic rows per dataset')
    stacked=[];stacked_failures=[]
    for p in (ROOT/'results'/'stacked').glob('*/*.json'):
        o=read(p);assert o['completed']
        if o['infeasible']:
            assert p.parent.name=='mawi2022_flow' and p.stem=='16' and len(o['infeasible'])==1 and not o['rows']
            assert o['infeasible'][0]['reason']=='side layers cannot fit'
            stacked_failures.append(dict(dataset='mawi2022_flow',budget_kib=16,source=str(p.relative_to(ROOT)),
                reason='Frozen implementation selected a feasible half-learning side layer whose all-learning rebuild cannot fit. It returned failure instead of the documented zero-layer fallback. Original result retained; no holdout replay or algorithm repair after seeing its outcome.'))
        assert o.get('zero_fallback_rechecked') or p.parent.name=='mawi2022_flow'
        for r in o['rows']:
            assert r['state_bytes']<=r['budget_kib']*1024 and r['member_false_negatives']==0
        stacked+=o['rows']
    counts['stacked_rows']=len(stacked);counts['stacked_failed_cases']=len(stacked_failures)
    assert len(stacked)==948 and len(stacked_failures)==1
    checks.append('Learning-tuned stacked:948 valid runs and one explicitly retained frozen-holdout construction failure; failed case excluded from FPR comparisons')
    native=[]
    for p in (ROOT/'results'/'aqf').glob('*.json'):
        o=read(p);assert o['completed']
        for r in o['rows']:
            assert r['feasible'] and r['fn_before']==r['fn_after']==0
            assert r['filter_allocated_bytes']<=r['budget_kib']*1024
            assert r['reverse_map_peak_bytes']>=r['reverse_map_allocated_bytes']>0
        native+=o['rows']
    counts['native_aqf_rows']=len(native);assert len(native)==342
    checks.append('Native upstream AdaptiveQF actual heap allocation fits high budgets; full members checked before/after; reverse-map allocation separate')
    ablation=[]
    for ds in ('cod','caida','caida_flow','mawi2021_flow'):
        o=read(ROOT/'results'/'ablations'/f'{ds}.json');assert o['completed'] and o['A1_fixed_common_window']
        assert len(o['completed_cases'])==(1 if ds.endswith('_flow') else 15)
        for r in o['rows']:
            assert r['actual_filter_state_bytes']<=r['budget_kib']*1024 and r['member_false_negatives']==0
            assert abs(r['fpr']-r['fp_tail']/r['evaluation_queries'])<1e-14
            if r['task']=='A1':
                assert r['common_last50pct']
                assert r['learning_queries']+r['unused_gap_queries']==r['evaluation_start_query']
                assert r['evaluation_queries']==r['queries']-r['evaluation_start_query']
        ablation+=o['rows']
    counts['ablation_rows']=len(ablation);assert len(ablation)==1152
    checks.append('32 ablation cases complete; all learning fractions share the same cold final50% window')
    hashes=[]
    for ds in ('caida_flow','mawi2021_flow'):
        o=read(ROOT/'results'/'hash_sensitivity'/f'{ds}.json');assert o['completed'] and len(o['completed_cases'])==15
        hashes+=o['rows']
    counts['hash_sensitivity_rows']=len(hashes);assert len(hashes)==150
    assert all(r['member_false_negatives']==0 and r['actual_filter_state_bytes']<=r['budget_kib']*1024 for r in hashes)
    live=[]
    for ds in ('cod','caida'):
        o=read(ROOT/'results'/'live'/f'{ds}.json');assert o['completed'] and len(o['rows'])==40
        for r in o['rows']:
            assert r['fn']==0 and r['raw_score_max_error']<1e-10 and r['state_bytes']<=r['budget_kib']*1024
            assert len(r['repeat_mean_query_ns'])==3 and r['accepted']==r['positive_queries']+r['fp']
            for b in r['backend_projections']:assert abs(b['projected_ns']-(r['mean_query_ns']+r['accepted']/r['evaluation_queries']*b['backend_us']*1000))<1e-6
        live+=o['rows']
    counts['live_rows']=len(live)
    sql=read(ROOT/'results'/'sqlite_backend.json');assert sql['completed'] and len(sql['rows'])==12
    assert all(r['false_negatives']==0 and r['backend_gets']==r['backend_hits']+r['backend_misses'] for r in sql['rows'])
    counts['real_backend_rows']=12
    dynamic=read(ROOT/'results'/'dynamic_members.json');assert dynamic['completed'] and dynamic['false_negatives']==0 and dynamic['inserted_members']==1000 and dynamic['removed_cache_records']>0
    assert dynamic['full_final_member_verification'] and dynamic['final_member_checks']==214045
    counts['dynamic_insertions']=1000
    for ds in ('cod','caida'):
        o=read(ROOT/'results'/f'recalibration_{ds}.json');assert o['completed'] and len(o['rows'])==5
        for r in o['rows']:
            assert r['member_false_negatives']==0 and r['retained_past_trace_bytes']==20000000
            assert [p['start_query'] for p in r['intervals']]==[2500000,5000000,7500000]
            assert r['periodic_fp']==sum(p['periodic_fp'] for p in r['intervals'])
    counts['periodic_recalibration_rows']=10
    checks.append('80 live paths with3 repeats,12 real SQLite runs,1000 sequential member insertions and10 drift recalibration runs verified')
    for name in ('fast-cache-tests','exact-replay-tests','live-pipeline-tests','A4-injected-prehash-collision','aqf-native-test'):
        assert read(ROOT/'evidence'/f'{name}.json')['status']=='passed'
    frozen=read(ROOT/'plan'/'final-holdout-freeze.json')
    assert all(sha(ROOT/p)==h for p,h in frozen['operational_source_sha256'].items())
    binary=read(ROOT/'evidence'/'native-binary-sha256.json');assert sha(ROOT/binary['binary'])==binary['sha256']
    checks.append('Operational code/protocol freeze unchanged after first MAWI2022 evaluation')
    backlog=read(ROOT/'plan'/'backlog.json');assert sha(Path(backlog['source']))==backlog['source_sha256']
    checks.append('User source workbook unchanged')
    # Read-only audit snapshot, save only into this round.
    import audit_existing as audit
    before=read(ROOT/'evidence'/'protected-before.json');after=audit.snapshot()
    b={r['path']:r for r in before['files']};a={r['path']:r for r in after['files']}
    diff=dict(added=sorted(a.keys()-b.keys()),missing=sorted(b.keys()-a.keys()),
              changed=sorted(p for p in a.keys()&b.keys() if a[p]['sha256']!=b[p]['sha256']),
              metadata_changed=sorted(p for p in a.keys()&b.keys() if a[p]['mtime_ns']!=b[p]['mtime_ns']))
    protected=dict(unchanged=not any(diff.values()),before_files=len(b),after_files=len(a),bytes=after['bytes'],**diff)
    E.save(ROOT/'evidence'/'protected-verification.json',protected);assert protected['unchanged']
    checks.append('Protected research/ and learned_adaptive_hybrid/ hashes and modification times unchanged')
    artifacts={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for pattern in ('results/**/*.json','tables/*.csv','cache/*/model*.txt','cache/*/preparation.json','cache/*/data.npz','cache/*/trace.npy','cache/*/gama_scores.npz') for p in ROOT.glob(pattern) if 'invalid_' not in str(p) and 'first_label_invalid' not in str(p) and 'httyf_subset' not in str(p)}
    E.save(ROOT/'evidence'/'result-and-model-sha256.json',artifacts)
    out=dict(status='passed',counts=counts,recorded_experiment_failures=stacked_failures,checks=checks,protected=protected,workbook_sha256=backlog['source_sha256'],verified_local=time.strftime('%Y-%m-%d %H:%M:%S'))
    E.save(ROOT/'results'/'verification.json',out);print(json.dumps(out,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':verify()

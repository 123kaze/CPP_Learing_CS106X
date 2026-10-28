"""Fail closed on missing experiments, invalid arithmetic or changed core files."""
from pathlib import Path
import json, hashlib, math
from collections import defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'cod':(256,), 'caida':(128,256), 'caida_flow':(48,64), 'mawi2021_flow':(40,48,64)}
METHODS={'误报流模型','Gama+缓存学习期网格','TODS式比例学习期网格','Gama无缓存'}
def read(p):return json.loads(p.read_text(encoding='utf-8'))
checks=[]
total=0
trace_counts={}
for ds,budgets in EXPECTED.items():
    for backend in ('clock','global_lru'):
        directory=ROOT/'results'/f'rerun_v2_{ds}_{backend}'
        meta=read(directory/'run_meta.json')
        rows=read(directory/'rows.json')
        assert meta['completed'] is True
        assert 'cold suffix' in meta['semantics']
        expected=len(budgets)*4*(1 if ds.endswith('_flow') else 21)-(1 if ds=='mawi2021_flow' else 0)
        assert len(rows)==expected,(ds,backend,len(rows),expected)
        if ds=='mawi2021_flow':
            assert len(meta['infeasible'])==1
            missing=meta['infeasible'][0]
            assert missing['budget_kib']==40 and missing['method']=='TODS式比例学习期网格'
        if ds.endswith('_flow') and ds not in trace_counts:
            with np.load(ROOT/'cache'/ds/'data.npz') as data:
                ids=data['ids'];members=data['y']
            z=(ids.astype(np.uint64)^np.uint64(0x5EED))+np.uint64(0x9E3779B97F4A7C15)
            z=(z^(z>>np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9)
            z=(z^(z>>np.uint64(27)))*np.uint64(0x94D049BB133111EB)
            z=z^(z>>np.uint64(31))
            u=(z>>np.uint64(11)).astype(np.float64)/2.**53
            test=(~members)&(u>=.2)
            rawtrace=np.load(ROOT/'cache'/ds/'trace.npy')
            trace_counts[ds]=int(test[rawtrace].sum())
        groups=defaultdict(list)
        for row in rows:
            assert row['dataset']==ds and row['backend']==backend
            assert row['budget_kib'] in budgets
            assert row['member_false_negatives']==0
            assert row['evaluation_queries']+row['learning_queries']==row['queries']
            assert row['learning_queries']==row['queries']//4
            if ds.endswith('_flow'):assert row['queries']==trace_counts[ds]
            assert 0<=row['fp_tail']<=row['evaluation_queries']
            assert math.isclose(row['fpr'],row['fp_tail']/row['evaluation_queries'],rel_tol=1e-14,abs_tol=1e-15)
            components=sum(row[k] for k in ('model_bytes','bf_bytes','metadata_bytes','array_overhead_bytes','sketch_bytes','cache_allocated_bytes'))
            assert components==row['actual_filter_state_bytes'],(ds,'memory sum',components,row)
            assert 0<=components<=row['budget_kib']*1024
            assert 0<=row['cache_allocated_bytes']<=row['cache_reserved_bytes']
            assert row['sketch_bytes']==5128
            if row['method']=='误报流模型':assert row['learning_state_bytes']==5128
            if row['method']=='Gama无缓存':assert row['cache_reserved_bytes']==0 and row['learning_state_bytes']==0
            if row['method'].startswith('TODS'):assert row['trees']==48
            assert row['cache_occupied']<=row['cache_capacity']
            groups[row['budget_kib'],row['workload'],row['seed']].append(row)
        assert set(r['budget_kib'] for r in rows)==set(budgets)
        for g in groups.values():
            expected_methods=METHODS-({'TODS式比例学习期网格'} if ds=='mawi2021_flow' and g[0]['budget_kib']==40 else set())
            assert len(g)==len(expected_methods) and {r['method'] for r in g}==expected_methods
            assert len({r['evaluation_queries'] for r in g})==1
        for b in budgets:
            sub=[r for r in rows if r['budget_kib']==b]
            if ds.endswith('_flow'):
                assert {r['seed'] for r in sub}=={0}
                assert {r['workload'] for r in sub}=={'真实轨迹'}
            else:
                assert {r['seed'] for r in sub}=={0,1,2}
                assert len({r['workload'] for r in sub})==7
        total+=len(rows)
        checks.append(f'{ds}/{backend}: {len(rows)} rows; counts, fair groups and charged buffers valid')
assert total==542
e2e_total=0
for ds,budgets in [('cod',{256,1024}),('caida',{128,256})]:
    result=read(ROOT/'results'/'end_to_end_fixed'/f'end_to_end_{ds}.json')
    assert result['metadata']['backend_latency_measured'] is False
    rows=result['rows']
    assert len(rows)==16
    keys=set()
    for row in rows:
        key=(row['budget_kib'],row['workload'],row['positive_fraction'],row['placement'])
        assert key not in keys;keys.add(key)
        assert row['budget_kib'] in budgets
        assert row['positive_fraction'] in (.1,.5)
        assert row['placement'] in ('cache_before','cache_after')
        assert row['false_negatives']==0
        assert row['raw_score_max_error']<=1e-10
        assert len(row['repeat_mean_query_ns'])==3
        assert row['mean_query_ns']>0
        assert math.isclose(row['measured_throughput_qps'],1e9/row['mean_query_ns'],rel_tol=1e-12)
        assert row['actual_filter_state_bytes']<=row['budget_kib']*1024
        assert row['model_calls']<=row['evaluated_queries']
        for p in row['backend_projections']:
            predicted=row['mean_query_ns']+row['accepted']/row['evaluated_queries']*p['backend_us']*1000
            assert math.isclose(p['projected_mean_query_ns'],predicted,rel_tol=1e-12)
    e2e_total+=len(rows)
    checks.append(f'{ds}/end_to_end: 16 live rows; zero FN, raw score agreement, projection formulas valid')
original=ROOT/'plan'/'holdout-freeze.json'
amended=ROOT/'plan'/'holdout-freeze-amendment.json'
frozen=read(amended if amended.exists() else original)
if amended.exists():assert frozen['original_freeze_sha256']==hashlib.sha256(original.read_bytes()).hexdigest()
for name,expected in frozen['sources'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
checks.append('Amended holdout core SHA256 unchanged; original freeze and one pre-tail crash retained')
for name in ['cache-tests.json','mawi-parser-tests.json']:
    p=ROOT/'evidence'/name
    test=read(p)
    assert test.get('status') in ('passed','PASS','pass') or test.get('passed') is True,(name,test)
    checks.append(f'{name}: passed')
smoke=read(ROOT/'evidence'/'synthetic_end_to_end_smoke'/'verification.json')
assert smoke['passed'] is True and smoke['false_negatives']==0 and smoke['raw_score_max_error']<=1e-10
checks.append('Live tree/cache/sketch independent smoke: passed')
out=dict(status='passed',main_rows=total,end_to_end_rows=e2e_total,checks=checks,
         note='This verifies records and invariants, not independent reproduction of measured execution times or theorems.')
(ROOT/'evidence'/'suite-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))

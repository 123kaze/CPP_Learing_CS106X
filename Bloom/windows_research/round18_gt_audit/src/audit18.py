"""Read-only audit of frozen learning counts; no model training, selection or repair.

Regenerates actual frozen query streams and checks archive stream hashes. A
literal missing-next-bin fallback is evaluated as a diagnostic array ONLY; it
is not installed in any selector, and its values never produce filter results.
"""
import os
for name in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name]='1'
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round12_nomodel/src'))
import baseline as B
sys.path.insert(0,str(WR/'round6_bucket/src'))
import holdout6  # registry only; never invokes prepare
import ra6
E5=B.E5
RA4=ra6.RA.ra4
MAIN=('cod','url','caida','shalla','caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow')
FLOW=('caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow','mawi2024_flow')
ALL=FLOW+tuple(x for x in MAIN if x not in FLOW)


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def ah(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()


def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(p)


def examine(learn):
    lm=RA4.summarize(learn,True)
    nc=np.bincount(lm.counts)
    N=lambda c:int(nc[c]) if c<len(nc) else 0
    gap=[c for c in range(1,6) if N(c)>0 and N(c+1)==0]
    nkeys=sum(N(c) for c in gap);nqueries=sum(c*N(c) for c in gap)
    all_singletons=bool(lm.L==len(lm.keys))
    # Counterfactual only. Preserve exact original values when the condition is absent.
    literal=lm.rate.copy()
    for c in gap:literal[lm.counts==c]=c/lm.L
    preserve_singletons=lm.rate.copy() if all_singletons else literal
    return dict(L=lm.L,distinct_keys=len(lm.keys),N_c_1_to_6={str(c):N(c) for c in range(1,7)},
                gap_c=gap,gap_keys=nkeys,gap_learning_queries=nqueries,gap_query_share=nqueries/lm.L,
                repeated_gap_c=[c for c in gap if c>=2],
                repeated_gap_keys=sum(N(c) for c in gap if c>=2),
                repeated_gap_query_share=sum(c*N(c) for c in gap if c>=2)/lm.L,
                singleton_gap_with_repeats=(1 in gap and not all_singletons),all_singletons=all_singletons,
                original_seen_rate_sum=float(lm.rate.sum()),original_unseen_mass=lm.N1/lm.L,
                original_total_mass=float(lm.rate.sum()+lm.N1/lm.L),all_rates_zero=bool(np.all(lm.rate==0)),
                total_collapse=bool(np.all(lm.rate==0) and lm.N1==0),
                literal_fallback_total_mass=float(literal.sum()+lm.N1/lm.L),
                preserve_singleton_fallback_total_mass=float(preserve_singletons.sum()+lm.N1/lm.L),
                literal_fallback_rate_bit_equal=(lm.rate.tobytes()==literal.tobytes()),
                preserve_singleton_fallback_rate_bit_equal=(lm.rate.tobytes()==preserve_singletons.tobytes()),
                counts_sha256=ah(lm.counts),keys_sha256=ah(lm.keys),original_rate_sha256=ah(lm.rate),
                literal_rate_sha256=ah(literal),preserve_singleton_rate_sha256=ah(preserve_singletons))


def references():
    rows=[];paths=[]
    for cohort,folder in (('main',WR/'round6_bucket/results/main'),('holdout',WR/'round6_bucket/results/holdout')):
        for p in sorted(folder.glob('rows_*.csv')):
            with p.open() as f:selected=[r for r in csv.DictReader(f) if r['method']=='RA6']
            for r in selected:rows.append(dict(cohort=cohort,dataset=r['dataset'],budget_kib=int(r['budget_kib']),workload=r['workload'],seed=int(r['seed'])))
            if selected:paths.append(p)
    assert sum(r['cohort']=='main' for r in rows)==1146
    assert sum(r['cohort']=='holdout' for r in rows)==4
    key=lambda r:(r['dataset'],r['budget_kib'],r['workload'],r['seed'])
    assert len({key(r) for r in rows})==1150
    baseline=WR/'round13_complete/results/combined_baseline_rows.csv';paths.append(baseline)
    with baseline.open() as f:paired={key(r):r for r in (
        dict(x,budget_kib=int(x['budget_kib']),seed=int(x['seed'])) for x in csv.DictReader(f) if x['cache']=='index')}
    for r in rows:
        ref=paired[key(r)]
        r.update(base_stream_sha256=ref['base_stream_sha256'],tail_len=int(ref['tail_len']))
    return rows,paths


def run(ds):
    out=ROOT/f'results/{ds}.json'
    assert not out.exists(),'Refuse to overwrite an audit record'
    archive,refpaths=references();subset=[r for r in archive if r['dataset']==ds]
    s,safe,inputs=B.load_setup(ds,'fp64')
    assert safe is None  # no training, safe-index construction or filter building
    q=s.split['neg_test'];assert not (s.split['member_train']&q).any()
    with np.load(B.C.CACHE/ds/'data.npz') as raw:
        assert not raw['y'][q].any(),'Learning pool contains members'
    specs=dict(E5.workload_specs(len(s.h1q))) if not ds.endswith('_flow') else {'真实轨迹':None}
    budgets=E5.BUDGETS[ds] if ds!='mawi2024_flow' else (16,24,32,128)
    seeds=range(1 if ds.endswith('_flow') else 5)
    expected={(ds,k,w,seed) for k in budgets for w in specs for seed in seeds}
    assert {(r['dataset'],r['budget_kib'],r['workload'],r['seed']) for r in subset}==expected
    sources={}
    for module in list(sys.modules.values()):
        fn=getattr(module,'__file__',None)
        if fn:
            p=Path(fn).resolve()
            if p.suffix=='.py' and p.is_relative_to(BLOOM) and not any(x.startswith('.condaenv') for x in p.relative_to(BLOOM).parts):sources[str(p.relative_to(BLOOM))]=digest(p)
    source_before=dict(sources)
    hashes={str(p.relative_to(BLOOM)):digest(p) for p in (*inputs,*refpaths)}
    grouped=defaultdict(list)
    for r in subset:grouped[r['workload'],r['seed']].append(r)
    streams=[];expanded=[]
    # Same frozen generator, with the deterministic score order prepared once.
    order=np.argsort(s.q_score,kind='stable') if not ds.endswith('_flow') else None
    for (name,seed),cases in sorted(grouped.items()):
        spec=specs[name]
        if spec is None:base=B.C.load_flow_trace(s)
        else:
            import exp2_repetition_cache as E2
            E2.QUERIES=10_000_000
            base=E5.R.make_stream(spec,len(s.h1q),np.random.default_rng(2000+seed),order)
        streamhash=ah(base)
        assert all(r['base_stream_sha256']==streamhash for r in cases),(ds,name,seed,'archive stream mismatch')
        n=len(base)//4
        assert all(r['tail_len']==len(base)-n for r in cases)
        diagnostic=examine(base[:n])
        record=dict(dataset=ds,cohort=cases[0]['cohort'],workload=name,seed=seed,base_len=len(base),pool_keys=len(s.h1q),
                    base_stream_sha256=streamhash,learning_stream_sha256=ah(base[:n]),budgets=[r['budget_kib'] for r in cases],**diagnostic)
        streams.append(record)
        expanded +=[dict(dataset=ds,cohort=r['cohort'],budget_kib=r['budget_kib'],workload=name,seed=seed,**diagnostic,
                         base_stream_sha256=streamhash) for r in cases]
        print(f'AUDIT {ds} {name} s{seed}: gaps={diagnostic["gap_c"]} all-singletons={diagnostic["all_singletons"]} '
              f'queries-affected={diagnostic["gap_learning_queries"]}/{n} mass={diagnostic["original_total_mass"]:.10f}',flush=True)
    for rel,h in hashes.items():assert digest(BLOOM/rel)==h,('read-only input changed',rel)
    for rel,h in source_before.items():assert digest(BLOOM/rel)==h,('source changed',rel)
    save(out,dict(status='complete',dataset=ds,cases=expanded,streams=streams,sources=sources,inputs=hashes,
                  numpy=np.__version__,scope='Counts only; no method installed/changed, no training, candidate selection or FP re-evaluation'))
    print(f'COMPLETE audit {ds}: {len(expanded)} cases / {len(streams)} workload-seed groups',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=ALL,required=True);run(p.parse_args().dataset)

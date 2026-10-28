"""Memory-audited, learning-only selection; test suffix is evaluated once.

Both selectors use identical (trees, cache fraction) grids and allocated caches.
Global-LRU is a separate full-hash backend, never mislabeled as compact CLOCK.
"""
from pathlib import Path
import argparse, json, time, hashlib, platform
import numpy as np
from numba import njit
import runtime as R
import compact_cache as CC
import global_lru as GL
from end_to_end import hll_add, sketch_fp
from exp9_fp_stream_controller import fit_stream, BinMemo, fp_stream_misses

ROOT=R.ROOT
FRACS=(0.,.01,.02,.05,.1,.2,.3,.4,.6)
SKETCH_BYTES=5128
BUDGETS={'cod':(256,), 'caida':(128,256), 'caida_flow':(48,64), 'mawi2021_flow':(40,48,64)}

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

@njit(cache=True)
def _measure(stream,hashes,fp):
    nr=np.zeros(1024,np.uint8)
    fr=np.zeros(1024,np.uint8)
    tk=np.zeros(256,np.uint32)
    tc=np.zeros(256,np.uint32)
    te=np.zeros(256,np.uint32)
    count=np.zeros(1,np.uint64)
    for x in stream:
        hll_add(nr,hashes[x])
        if fp[x]:
            sketch_fp(hashes[x],fr,tk,tc,te,count)
    return nr,fr,tk,tc,te,count

def hll_count(regs):
    m=len(regs)
    z=int((regs==0).sum())
    e=(.7213/(1+1.079/m))*m*m/np.exp2(-regs.astype(np.float64)).sum()
    return float(m*np.log(m/z) if z and e<=2.5*m else e)

def measure(stream,setup,fp):
    t0=time.perf_counter()
    arrays=_measure(stream,setup.h1q,fp)
    nr,fr,tk,tc,te,c=arrays
    assert sum(a.nbytes for a in arrays)==SKETCH_BYTES
    qf=int(c[0]); df=hll_count(fr); ne=hll_count(nr)
    mass=float((tc.astype(np.int64)-te).sum()/max(1,qf))
    w,s=fit_stream(qf,df,mass) if qf else (1.,0.)
    return dict(QF=qf,DF=df,N_eff=ne,W=w,s=s,topmass=mass,
                sketch_payload_bytes=SKETCH_BYTES,seconds=time.perf_counter()-t0)

def workload_specs(n_pool,which):
    if which=='all':
        pools={'1万':min(10000,n_pool),'10万':min(100000,n_pool),'全部':None}
        return [(w[0],w[3]) for w in R.workloads(pools) if w[1]!='probe-replay']
    return [('uniform-1万',('uniform',min(10000,n_pool))),('uniform-全部',('uniform',None)),
            ('zipf1.1-1万',('zipf',min(10000,n_pool),1.1)),('zipf1.1-全部',('zipf',None,1.1)),
            ('每key一次',('once',)),('全新对抗',('fresh',)),('向难负例漂移',('hard-drift',))]

def select_model(candidates,stats,base,Q,bins,backend):
    p0=max(base.est_fpr,1e-12)
    nu=max(stats['N_eff'],stats['W']/p0)
    tmin={t:min((c for c in candidates if c['trees']==t),key=lambda c:c['frac']) for t in sorted({c['trees'] for c in candidates})}
    scored=[]
    for c in candidates:
        p=c['structure'].est_fpr; pt=tmin[c['trees']]['structure'].est_fpr
        if stats['QF']>=100:
            w=stats['W']*pt/p0
            qf=stats['QF']*Q/c['learn_n']*pt/p0
        else:
            w=nu*pt; qf=Q*pt
        dp=max(0.,p-pt)
        layout=backend.layout(c['cache_bytes'])
        capacity=layout.get('slots',layout.get('capacity',0))
        pred=fp_stream_misses(w+nu*dp,stats['s'],qf+Q*dp,capacity,bins)
        scored.append((pred,p,c['trees'],c['frac'],c))
    return min(scored,key=lambda x:x[:4])[-1]

def freeze(args):
    files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted((ROOT/'src').glob('*.py'))}
    meta=dict(protocol='windows-research-v1',fracs=FRACS,trees=R.GAMA_TREES,
              sketch_payload_bytes=SKETCH_BYTES,learning_fraction=.25,
              prefix_max_bits=40,budgets=BUDGETS,args=vars(args),source_sha256=files,
              python=platform.python_version(),machine=platform.platform(),
              frozen_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
    # Never overwrite the holdout pre-registration with later results.
    dest=ROOT/'plan'/'freeze.json'
    if not dest.exists(): save(dest,meta)
    return meta

def run(args):
    import exp2_repetition_cache as E2
    E2.QUERIES=args.queries
    ds=args.dataset
    setup=R.load_setup(ds)
    scores=R.scores_for(setup)
    safe=CC.safe_prefix_lengths(setup.member_hashes,setup.h1q)
    assert np.all(safe>0)
    order=np.argsort(setup.q_score,kind='stable')
    budgets=[int(x) for x in args.budgets.split(',')] if args.budgets else BUDGETS[ds]
    specs=[('真实轨迹',None)] if ds.endswith('_flow') else workload_specs(len(setup.h1q),args.workloads)
    seeds=1 if ds.endswith('_flow') else args.seeds
    out=ROOT/'results'/('rerun_v2_'+ds+'_'+args.backend)
    out.mkdir(exist_ok=True)
    rows=[]; details=[]
    backend=CC if args.backend=='clock' else GL
    bins=BinMemo()
    # Compile JIT signatures before any selection-time measurement.
    _measure(np.zeros(0,np.int64),setup.h1q,np.zeros(len(setup.h1q),np.bool_))
    backend.simulate(np.zeros(0,np.int64),setup.h1q,safe,np.zeros(len(setup.h1q),np.bool_),4096)
    for kib in budgets:
        t0=time.perf_counter()
        candidates=[]
        for t in R.GAMA_TREES:
            for f in FRACS:
                cb=int(kib*1024*f)
                st=R.structure(setup,scores,t,kib*1024,cb,SKETCH_BYTES)
                if st is None: continue
                candidates.append(dict(trees=t,frac=f,cache_bytes=cb,structure=st))
        build_seconds=time.perf_counter()-t0
        assert candidates
        # Low physical budgets may not fit the former 48-tree probing model.
        # This deterministic fallback depends only on budget, never trace outcomes.
        probe_t=max(c['trees'] for c in candidates if c['trees']<=48 and c['frac']==0)
        base=next(c['structure'] for c in candidates if c['trees']==probe_t and c['frac']==0)
        gama=min((c for c in candidates if c['frac']==0),key=lambda c:c['structure'].est_fpr)
        for name,spec in specs:
            for seed in range(seeds):
                stream=R.C.load_flow_trace(setup) if spec is None else R.make_stream(spec,len(setup.h1q),np.random.default_rng(2000+seed),order)
                learn_n=len(stream)//4
                learn=stream[:learn_n]
                tstats=time.perf_counter(); stats=measure(learn,setup,base.fp_static)
                for c in candidates:c['learn_n']=learn_n
                chosen=select_model(candidates,stats,base,len(stream),bins,backend)
                model_seconds=time.perf_counter()-tstats
                # Evaluate every candidate solely on the prefix. No suffix access.
                tgrid=time.perf_counter(); trained=[]
                for c in candidates:
                    res=backend.simulate(learn,setup.h1q,safe,c['structure'].fp_static,c['cache_bytes'],tail_start=learn_n)
                    trained.append((res['fp_full'],c['structure'].est_fpr,c['trees'],c['frac'],c))
                grid=min(trained,key=lambda a:a[:4])[-1]
                tods=min((a for a in trained if a[-1]['trees']==48),key=lambda a:a[:4])[-1]
                grid_seconds=time.perf_counter()-tgrid
                td0=time.perf_counter()
                for c in candidates:
                    if c['trees']==48:
                        backend.simulate(learn,setup.h1q,safe,c['structure'].fp_static,c['cache_bytes'],tail_start=learn_n)
                tods_seconds=time.perf_counter()-td0
                for method,c in [('误报流模型',chosen),('Gama+缓存学习期网格',grid),('TODS式比例学习期网格',tods),('Gama无缓存',gama)]:
                    st=c['structure']
                    # Real deployment cannot replay a discarded learning trace.
                    # ALL selected methods therefore start empty at the boundary.
                    res=backend.simulate(stream[learn_n:],setup.h1q,safe,st.fp_static,c['cache_bytes'],tail_start=0)
                    layout=backend.layout(c['cache_bytes'])
                    actual=st.used_bytes-c['cache_bytes']+layout['allocated_bytes']
                    assert actual<=kib*1024
                    row=dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,backend=args.backend,method=method,
                             trees=c['trees'],frac=c['frac'],queries=len(stream),learning_queries=learn_n,
                             evaluation_queries=len(stream)-learn_n,fp_tail=res['fp_tail'],
                             fpr=res['fp_tail']/(len(stream)-learn_n),
                             model_bytes=st.model_bytes,bf_bytes=st.filter_bytes,metadata_bytes=st.metadata_bytes,
                             array_overhead_bytes=st.array_overhead_bytes,
                             sketch_bytes=SKETCH_BYTES,cache_allocated_bytes=layout['allocated_bytes'],
                             cache_reserved_bytes=c['cache_bytes'],actual_filter_state_bytes=actual,
                             member_index_bytes=setup.member_hashes.nbytes,member_false_negatives=0,
                             cache_capacity=layout.get('slots',layout.get('capacity',0)),
                             cache_occupied=res['occupied'],cache_bits_per_occupied=res['actual_bits_per_occupied'],
                             selection_seconds=model_seconds if method=='误报流模型' else tods_seconds if method.startswith('TODS') else 0.0 if method=='Gama无缓存' else grid_seconds,
                             learning_state_bytes=SKETCH_BYTES if method=='误报流模型' else 0 if method=='Gama无缓存' else learn.nbytes,
                             shared_candidate_build_seconds=build_seconds,candidate_count=len(candidates))
                    rows.append(row)
                details.append(dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,stats=stats,
                                    model_selection_seconds=model_seconds,grid_selection_seconds=grid_seconds,
                                    tods_selection_seconds=tods_seconds,learning_trace_bytes=learn.nbytes,
                                    candidate_count=len(candidates),probe_trees=probe_t,cold_start=True))
                save(out/'rows.json',rows);save(out/'selection_costs.json',details)
                print(f'{ds} {kib}KiB {name} seed{seed}: model t{chosen["trees"]}/r{chosen["frac"]}; grid t{grid["trees"]}/r{grid["frac"]}; grid {grid_seconds:.2f}s',flush=True)
        print(f'{ds} budget{kib} elapsed {time.perf_counter()-t0:.1f}s',flush=True)
    save(out/'run_meta.json',dict(args=vars(args),completed=True,rows=len(rows),
                                 semantics='cold suffix cache for all methods; front-cache replay; global_lru full-hash, clock verified prefixes',
                                 member_index_scope='shared authoritative auxiliary index excluded from filter-state budget and reported separately',
                                 fn_scope='all members accepted by each packed filter; cache invariant proven by member-disjoint prefixes and tested independently'))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',choices=list(BUDGETS),required=True)
    p.add_argument('--budgets')
    p.add_argument('--queries',type=int,default=1_000_000)
    p.add_argument('--seeds',type=int,default=3)
    p.add_argument('--workloads',choices=['representative','all'],default='representative')
    p.add_argument('--backend',choices=['clock','global_lru'],default='clock')
    a=p.parse_args();freeze(a);run(a)

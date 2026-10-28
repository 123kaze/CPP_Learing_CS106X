"""Full-scale non-C experiments, checkpointed after every shared workload seed."""
import argparse,time,json
import numpy as np
import engine as E
from pathlib import Path

def run(ds,budgets,queries=10000000,seeds=5,limit_workloads=None):
    setup,scores,safe=E.load(ds)
    out=E.ROOT/'results'/'main'/ds
    out.mkdir(parents=True,exist_ok=True)
    E.OLD._measure(np.zeros(0,np.int64),setup.h1q,np.zeros(len(setup.h1q),np.bool_))
    E.F.simulate(np.zeros(0,np.int64),setup.h1q,safe,np.zeros(len(setup.h1q),np.bool_),4096)
    specs=[('真实轨迹',None,'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
    if limit_workloads:specs=[w for w in specs if w[0] in limit_workloads]
    if ds.endswith('_flow'):seeds=1
    for kib in budgets:
        dest=out/f'{kib}.json'
        previous=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else dict(rows=[],selections=[],infeasible=[],completed=False)
        if previous['completed']:continue
        rows=previous['rows'];details=previous['selections'];infeasible=previous['infeasible']
        done={(r['workload'],r['seed']) for r in details}
        t=time.perf_counter();cands=E.candidates(setup,scores,kib);build_seconds=time.perf_counter()-t
        zeros=[c for c in cands if c['frac']==0]
        gama=min(zeros,key=lambda c:(c['structure'].est_fpr,c['trees']))
        probe=max((c for c in zeros if c['trees']<=48),key=lambda c:c['trees'])
        plains=[E.build_plain(setup,kib,f) for f in E.FRACS];plains=[c for c in plains if c]
        bins=E.BinMemo()
        for name,spec,family in specs:
            for seed in range(seeds):
                if (name,seed) in done:continue
                start=time.perf_counter()
                stream=E.stream_for(setup,name,spec,family,seed,queries,gama['structure'])
                learn_n=len(stream)//4;learn=stream[:learn_n];tail=stream[learn_n:]
                ts=time.perf_counter();stats=E.measure(learn,setup,probe['structure'])
                ranking=E.rank(cands,stats,probe['structure'],len(tail),learn_n,bins)
                model=ranking[0][-1];model_seconds=time.perf_counter()-ts
                grid,fixed,grid_seconds,records=E.exact_grid(ranking,learn,setup,safe)
                plain,_,plain_seconds,_=E.exact_grid(plains,learn,setup,safe,track48=False)
                ski=E.build(setup,scores,model['trees'],kib,model['frac'],admit=2)
                frequencies=np.bincount(tail,minlength=len(setup.h1q))
                methods=[('Gama',gama,0),('StreamModel',model,model_seconds),('LearnGrid',grid,grid_seconds),
                         ('Fixed48Grid',fixed,grid_seconds),('BFCacheGrid',plain,plain_seconds),('SkiQFAdmission2',ski,model_seconds)]
                for method,c,seconds in methods:
                    if c is None:
                        infeasible.append(dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,method=method,reason='cannot fit physical budget'));continue
                    result=E.evaluate(c,tail,setup,safe,frequencies)
                    r=E.row(c,result,ds,kib,name,seed,method,len(stream),learn_n,seconds)
                    r['member_index_bytes']=setup.member_hashes.nbytes
                    r['exact_replay_optimization']=result['optimization']
                    r['learning_trace_bytes']=learn.nbytes if method in ('LearnGrid','BFCacheGrid','Fixed48Grid') else 0
                    r['learning_peak_filter_and_stats_bytes']=c['structure'].used_bytes+(5128+6*E.F.ARRAY_HEADER if method=='StreamModel' else 0)
                    rows.append(r)
                details.append(dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,queries=len(stream),learning_queries=learn_n,
                                    model_seconds=model_seconds,grid_seconds=grid_seconds,plain_seconds=plain_seconds,
                                    stats=stats,candidate_count=len(cands),exact_candidates=sum(r['exact'] for r in records),
                                    grid_processed_queries=sum(r['processed'] for r in records),naive_grid_queries=len(cands)*learn_n,
                                    shared_build_seconds=build_seconds,ordered_grid=records,
                                    model_rank=[dict(trees=r[-1]['trees'],frac=r[-1]['frac'],predicted_fp=r[0]) for r in ranking]))
                E.save(dest,dict(rows=rows,selections=details,infeasible=infeasible,completed=False,
                                 queries=queries,seeds=seeds,features='address_only' if ds.endswith('_flow') else 'original',
                                 protocol='F1 free deployment sketch, F2 refund cache slack, prefix-only selection, cold suffix'))
                print(f'{ds} {kib}KiB {name} seed{seed} done {time.perf_counter()-start:.2f}s grid={grid_seconds:.2f}s ({sum(r["processed"] for r in records)/max(1,len(cands)*learn_n):.1%} replayed)',flush=True)
        result=json.loads(dest.read_text(encoding='utf-8'));result['completed']=True;E.save(dest,result)
        print(f'COMPLETE {ds}/{kib}: {len(rows)} valid rows',flush=True)
        del cands,plains
        E.R._GSETUPS.clear()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--budgets');p.add_argument('--queries',type=int,default=10000000);p.add_argument('--seeds',type=int,default=5);p.add_argument('--workloads')
    a=p.parse_args();run(a.dataset,[int(x) for x in a.budgets.split(',')] if a.budgets else E.BUDGETS[a.dataset],a.queries,a.seeds,a.workloads.split(',') if a.workloads else None)

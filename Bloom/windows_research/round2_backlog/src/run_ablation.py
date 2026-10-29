"""Predeclared non-C ablations at full query count; checkpoint every case."""
import argparse,time,json
import numpy as np
from functools import lru_cache
import engine as E
import policy_replay as P
SETTINGS={'cod':256,'caida':128,'caida_flow':24,'mawi2021_flow':24}
NAMES={'uniform-1万','zipf1.1-全部','向难负例漂移'}

def run(ds):
    kib=SETTINGS[ds];setup,scores,safe=E.load(ds)
    cands=E.candidates(setup,scores,kib)
    # A filter depends on data/budget/configuration, never on the workload seed.
    # Reuse identical read-only structures instead of rebuilding every case.
    fine=(0.,.0005,.001,.002,.003,.005,.0075,.01,.0125,.015,.0175,.02,.05,.1,.2,.3,.4,.6)
    existing={(c['trees'],c['frac']):c for c in cands}
    fine_cands=[existing.get((t,f)) or E.build(setup,scores,t,kib,f) for t in E.R.GAMA_TREES for f in fine]
    fine_cands=[c for c in fine_cands if c is not None]
    @lru_cache(maxsize=24)
    def variant(t,f,policy='clock',prefix=40,ways=4):
        if policy=='clock' and prefix==40 and ways==4 and (t,f) in existing:return existing[t,f]
        return E.build(setup,scores,t,kib,f,policy=policy,prefix=prefix,ways=ways)
    @lru_cache(maxsize=4)
    def global_structure(t,cache):return E.R.structure(setup,scores,t,kib*1024,cache,0)
    zero=[c for c in cands if c['frac']==0]
    gama=min(zero,key=lambda c:c['structure'].est_fpr)
    probe=max([c for c in zero if c['trees']<=48],key=lambda c:c['trees'])
    specs=[('真实轨迹',None,'trace')] if ds.endswith('_flow') else [w for w in E.workload_specs(len(setup.h1q)) if w[0] in NAMES]
    seeds=1 if ds.endswith('_flow') else 5
    dest=E.ROOT/'results'/'ablations'/f'{ds}.json';dest.parent.mkdir(exist_ok=True)
    obj=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else dict(rows=[],completed_cases=[],completed=False)
    if obj['completed']:return
    done={tuple(x) for x in obj['completed_cases']};bins=E.BinMemo()
    E.OLD._measure(np.zeros(0,np.int64),setup.h1q,np.zeros(len(setup.h1q),np.bool_))
    for name,spec,family in specs:
        for seed in range(seeds):
            if (name,seed) in done:continue
            ts=time.perf_counter();stream=E.stream_for(setup,name,spec,family,seed,10000000,gama['structure'])
            n=len(stream)//4;learn=stream[:n];tail=stream[n:];freq=np.bincount(tail,minlength=len(setup.h1q))
            stats=E.measure(learn,setup,probe['structure']);ranking=E.rank(cands,stats,probe['structure'],len(tail),n,bins)
            chosen=ranking[0][-1]
            def add(task,variant,c,part=tail,frequencies=freq,learning_fraction=.25,**extra):
                result=E.evaluate(c,part,setup,safe,frequencies)
                record=E.row(c,result,ds,kib,name,seed,variant,len(stream),len(stream)-len(part))
                record.update(task=task,variant=variant,learning_fraction=learning_fraction,member_index_bytes=setup.member_hashes.nbytes,**extra)
                obj['rows'].append(record)
                return result
            # A1: every fraction uses only its own prefix; all suffix caches cold.
            for fraction in (.05,.10,.25,.50):
                ln=int(len(stream)*fraction);lrn=stream[:ln];test=stream[ln:]
                fqs=np.bincount(test,minlength=len(setup.h1q))
                st=E.measure(lrn,setup,probe['structure']);rank=E.rank(cands,st,probe['structure'],len(test),ln,bins)
                grid,_,seconds,_=E.exact_grid(rank,lrn,setup,safe,track48=False)
                for label,c in [('model',rank[0][-1]),('grid',grid),('Gama',gama)]:
                    add('A1',label,c,test,fqs,learning_fraction=fraction,selection_grid_seconds=seconds)
            # A2: k distinct physical configurations, not duplicate reservations.
            unique=[];seen=set()
            for rank in ranking:
                c=rank[-1];key=(c['trees'],c['cache_bytes'])
                if key not in seen:unique.append(c);seen.add(key)
            tp=time.perf_counter();training=[]
            for c in unique[:10]:
                result=E.simulate(c,learn,setup,safe)
                training.append((result['fp'],c['structure'].est_fpr,c['trees'],c['frac'],c))
            top10_seconds=time.perf_counter()-tp
            for k in (3,5,10):
                best=min(training[:k],key=lambda x:x[:4])[-1]
                add('A2',f'top{k}',best,top10_total_replay_seconds=top10_seconds,
                    distinct_candidate_count=len(unique),k=k)
            # A3: implementation sensitivity at a fixed selected tree/share.
            for policy in ('clock','bucket_lru','bucket_fifo','global_lru','global_fifo'):
                if policy.startswith('global'):
                    requested=chosen['requested_cache_bytes'];layout=P.G.layout(requested)
                    st=global_structure(chosen['trees'],layout['allocated_bytes'])
                    result=P.run(policy,tail,setup,safe,st.fp_static,layout['allocated_bytes'])
                    obj['rows'].append(dict(task='A3',variant=policy,dataset=ds,budget_kib=kib,workload=name,seed=seed,
                                            trees=chosen['trees'],frac=chosen['frac'],fp_tail=result['fp'],fpr=result['fp']/len(tail),
                                            evaluation_queries=len(tail),cache_allocated_bytes=result['cache_allocated_bytes'],
                                            cache_capacity=result['capacity'],actual_filter_state_bytes=st.used_bytes,
                                            member_false_negatives=0,
                                            note='Full-hash matching and metadata differ from prefix caches; not a pure replacement-policy effect'))
                else:
                    code='fifo' if policy=='bucket_fifo' else policy
                    c=variant(chosen['trees'],chosen['frac'],policy=code)
                    add('A3',policy,c,cache_capacity=E.F.layout(c['cache_bytes'],policy=code)['slots'])
            # A4: unchecked full64 hash is exact for original scalar64 keys;
            # unbounded URL/flow keys were already hashed before this cache.
            add('A4','verified_prefix',chosen)
            unchecked=variant(chosen['trees'],chosen['frac'],prefix=64)
            lengths=np.full(len(safe),64,np.int16)
            result=E.F.simulate(tail,setup.h1q,lengths,unchecked['structure'].fp_static,unchecked['cache_bytes'],prefix_bits=64,collect=True)
            record=E.row(unchecked,result,ds,kib,name,seed,'unchecked64',len(stream),n)
            record.update(task='A4',variant='unchecked64',member_index_bytes=0,
                          collision_scope='bijective hashing of scalar64 IDs' if ds in ('cod','caida') else 'probabilistic for unbounded original keys; no observed dataset collision')
            obj['rows'].append(record)
            # A6: complete predeclared 4x3 layout sensitivity, tree/share fixed.
            for prefix in (24,32,40,56):
                for ways in (2,4,8):
                    c=variant(chosen['trees'],chosen['frac'],prefix=prefix,ways=ways)
                    add('A6',f'prefix{prefix}_ways{ways}',c,prefix_bits=prefix,ways=ways)
            fine_rank=E.rank(fine_cands,stats,probe['structure'],len(tail),n,bins)
            fg,_,seconds,_=E.exact_grid(fine_rank,learn,setup,safe,track48=False)
            add('A6','fine_grid_model',fine_rank[0][-1],fine_grid_selection_seconds=seconds)
            add('A6','fine_grid_exact',fg,fine_grid_selection_seconds=seconds)
            obj['completed_cases'].append([name,seed]);E.save(dest,obj)
            print(f'ABLATIONS {ds}/{kib} {name} seed{seed} {time.perf_counter()-ts:.1f}s',flush=True)
    obj['completed']=True;E.save(dest,obj)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=SETTINGS,required=True);a=p.parse_args();run(a.dataset)

"""Actual live traversal for selected configurations; sketch released at deploy."""
import time,json
import numpy as np
import lightgbm as lgb
from numba import njit
import engine as E
import end_to_end as Old

@njit(cache=True,inline='always')
def hash_key(value):
    return Old.mix64((np.uint64(value)^np.uint64(0xA5A50001))+np.uint64(0x9E3779B97F4A7C15))

@njit(cache=True)
def query_one(X,ids,row,feat,thr,left,right,leaf,roots,cuts,kind,off,m,k,bits,
              slab,q,r,sb,ways,code,hb,placement):
    h=hash_key(ids[row])
    if q and placement==0 and E.F.lookup(slab,h,q,r,sb,ways,code):return False,h,True,False
    score=Old.model_score(X[row],feat,thr,left,right,leaf,roots)
    if not Old.filter_query(score,h,cuts,kind,off,m,k,bits):return False,h,False,True
    if q and placement==1 and E.F.lookup(slab,h,q,r,sb,ways,code):return False,h,True,True
    return True,h,False,True

@njit(cache=True)
def feedback(slab,h,members,q,r,sb,ways,code,hb):
    if not q:return 0
    length=E.CC.safe_prefix_length(members,h)
    return E.F.insert(slab,h,length,q,r,sb,ways,code,hb)

@njit(cache=True)
def run(X,ids,y,stream,feat,thr,left,right,leaf,roots,cuts,kind,off,m,k,bits,
        slab,members,q,r,sb,ways,code,hb,placement):
    # backend accepts,FP,FN,hits,inserts,evictions,index searches,model calls,
    # cache probes,negative requests,positive requests.
    out=np.zeros(11,np.int64)
    for row in stream:
        h=hash_key(ids[row]);member=y[row]
        if member:out[10]+=1
        else:out[9]+=1
        hit=False
        if q and placement==0:
            out[8]+=1;hit=E.F.lookup(slab,h,q,r,sb,ways,code)
        if hit:
            out[3]+=1;out[2]+=member;continue
        if len(roots):out[7]+=1
        score=Old.model_score(X[row],feat,thr,left,right,leaf,roots)
        accepted=Old.filter_query(score,h,cuts,kind,off,m,k,bits)
        if not accepted:
            out[2]+=member;continue
        if q and placement==1:
            out[8]+=1;hit=E.F.lookup(slab,h,q,r,sb,ways,code)
        if hit:
            out[3]+=1;out[2]+=member;continue
        out[0]+=1
        if not member:
            out[1]+=1
            if q:
                out[6]+=1;status=feedback(slab,h,members,q,r,sb,ways,code,hb)
                out[4]+=status>0;out[5]+=status==2
    return out

def select(setup,scores,kib,mixed,learning_fraction=.25):
    n=int(len(mixed)*learning_fraction)
    testrows=np.flatnonzero(setup.split['neg_test'])
    to_pool=np.full(len(setup.ids),-1,np.int32);to_pool[testrows]=np.arange(len(testrows))
    idx=mixed[:n];neg=idx[~setup.y[idx]];learn=to_pool[neg].astype(np.int64)
    assert (learn>=0).all()
    cands=E.candidates(setup,scores,kib)
    zeros=[c for c in cands if c['frac']==0]
    gama=min(zeros,key=lambda c:c['structure'].est_fpr)
    probe=max((c for c in zeros if c['trees']<=48),key=lambda c:c['trees'])
    # The requested positive ratio is a declared workload parameter.
    negative_fraction=len(learn)/max(1,n)
    start=time.perf_counter();stats=E.measure(learn,setup,probe['structure'])
    ranks=E.rank(cands,stats,probe['structure'],max(1,int((len(mixed)-n)*negative_fraction)),len(learn),E.BinMemo())
    model_seconds=time.perf_counter()-start
    grid,_,seconds,_=E.exact_grid(ranks,learn,setup,E.CC.safe_prefix_lengths(setup.member_hashes,setup.h1q),track48=False)
    return [('Gama',gama),('StreamModel',ranks[0][-1]),('LearnGrid',grid)],dict(learning_queries=n,learning_negative_queries=len(learn),grid_seconds=seconds,model_seconds=model_seconds,retained_grid_trace_bytes=learn.nbytes,model_statistics_payload_bytes=5128,stats=stats,grid_implementation='physical-layout memo; exact no-eviction bound; monotone early stop; shared frequencies')

class Executable:
    def __init__(self,setup,X,c,placement=0):
        self.setup=setup;self.X=X;self.c=c;self.placement=placement
        self.layout=E.F.layout(c['cache_bytes'],c['prefix_bits'],c['policy'],c['ways'])
        self.slab=E.F.allocate(self.layout)
        st=c['structure'];tree=st.model_arrays
        if tree is None:
            tree={k:np.empty(0,np.int16 if k in ('feat','left','right','roots') else np.float64) for k in Old.TREE_KEYS}
        self.tree=tree
        self.arrays=tuple(tree[k] for k in Old.TREE_KEYS)+(st.cuts,st.kind,st.bf_off,st.m,st.k,st.bits)
    def reset(self):self.slab=E.F.allocate(self.layout)
    def args(self):
        s=self.layout
        return (self.slab,s['qbits'],s['rbits'],s['slot_bits'],s['ways'],s['policy_code'],s['handbits'],self.placement)
    def batch(self,stream):
        s=self.layout
        return run(self.X,self.setup.ids,self.setup.y,stream,*self.arrays,self.slab,self.setup.member_hashes,
                   s['qbits'],s['rbits'],s['slot_bits'],s['ways'],s['policy_code'],s['handbits'],self.placement)
    def probe(self,row):return query_one(self.X,self.setup.ids,row,*self.arrays,*self.args())
    def insert(self,h):
        s=self.layout
        return feedback(self.slab,np.uint64(h),self.setup.member_hashes,s['qbits'],s['rbits'],s['slot_bits'],s['ways'],s['policy_code'],s['handbits'])

def benchmark(ds,budgets,queries=1000000,repeats=3):
    setup,scores,safe=E.load(ds)
    _,_,X,_=E.C.load_dataset(ds);X=np.ascontiguousarray(X)
    booster=lgb.Booster(model_file=str(E.C.CACHE/ds/'model200.txt'))
    out=E.ROOT/'results'/'live';out.mkdir(exist_ok=True)
    rows=[];selections=[]
    for kib in budgets:
        for workload in ('uniform','zipf1.1-10k'):
            for positive in (.1,.5):
                mixed=Old.make_mixed_stream(setup,positive,queries,workload)
                n=queries//4;configs,stats=select(setup,scores,kib,mixed)
                selections.append(dict(budget_kib=kib,workload=workload,positive_fraction=positive,
                                       configs=[dict(method=name,trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes']) for name,c in configs],**stats))
                for method,c in configs:
                    sample=np.arange(0,len(X),max(1,len(X)//5000))
                    pred=Old.predict_raw(X[sample],*(c['structure'].model_arrays[k] for k in Old.TREE_KEYS))
                    ref=booster.predict(X[sample],raw_score=True,num_iteration=c['trees'],num_threads=1)
                    error=float(np.max(np.abs(pred-ref)));assert error<1e-10
                    for placement in ((0,) if method=='Gama' else (0,1)):
                        exe=Executable(setup,X,c,placement)
                        exe.batch(mixed[:1000]) # JIT warmup on discarded cache, no learning replay.
                        times=[];counts=[]
                        for rep in range(repeats):
                            exe.reset();start=time.perf_counter_ns();result=exe.batch(mixed[n:]);elapsed=time.perf_counter_ns()-start
                            assert result[2]==0
                            times.append(elapsed/(queries-n));counts.append(result)
                        assert all(np.array_equal(counts[0],value) for value in counts)
                        ct=counts[0];cpu=float(np.median(times));q=queries-n
                        row=dict(dataset=ds,budget_kib=kib,workload=workload,positive_fraction=positive,method=method,
                                 placement='before' if placement==0 else 'after',trees=c['trees'],frac=c['frac'],
                                 cache_bytes=c['cache_bytes'],state_bytes=c['structure'].used_bytes,
                                 required_member_index_bytes=setup.member_hashes.nbytes+E.F.ARRAY_HEADER if c['cache_bytes'] else 0,
                                 evaluation_queries=q,mean_query_ns=cpu,repeat_mean_query_ns=times,throughput_qps=1e9/cpu,
                                 accepted=int(ct[0]),fp=int(ct[1]),fn=int(ct[2]),cache_hits=int(ct[3]),
                                 inserts=int(ct[4]),evictions=int(ct[5]),member_index_searches=int(ct[6]),model_calls=int(ct[7]),cache_probes=int(ct[8]),
                                 negative_queries=int(ct[9]),positive_queries=int(ct[10]),raw_score_max_error=error,
                                 cold_suffix=True,sketch_deployed_bytes=0,
                                 selection_scope='own first25% mixed queries, only observed negative feedback',
                                 includes='hash/live tree/BF/cache/member verification/feedback; no feature extraction or I/O')
                        row['backend_projections']=[dict(backend_us=us,projected_ns=cpu+row['accepted']/q*us*1000,
                                                             projected_qps=1e9/(cpu+row['accepted']/q*us*1000)) for us in (1,10,100)]
                        rows.append(row);E.save(out/f'{ds}.json',dict(rows=rows,selections=selections,completed=False))
                        print(f'LIVE {ds}/{kib} {workload} p{positive} {method} {row["placement"]} {cpu:.1f}ns FP={row["fp"]}',flush=True)
    E.save(out/f'{ds}.json',dict(rows=rows,selections=selections,completed=True))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--budgets',required=True);a=p.parse_args();benchmark(a.dataset,list(map(int,a.budgets.split(','))))

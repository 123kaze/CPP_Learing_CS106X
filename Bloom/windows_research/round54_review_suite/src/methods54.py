"""Zero-tree controls, exhaustive weighted candidates and identical-frequency reorderings."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shared54 import *


def zero(ds,seed):
    check();start=time.perf_counter();d=load(ds,seed);rows=[];cases=[]
    if ds in TCP:ks=TCP[ds]['budgets_kib'];streams=[('original',d.learn,d.tail)]
    elif ds=='clark':ks=(8,16,32);streams=[('original',d.learn,d.tail)]
    else:
        ks=(64,128,256);streams=[]
        for name,spec in (('once',('once',)),('fresh',('fresh',))):
            base=E5.base_stream(d.s,name,spec,0,10000000);n=len(base)//4;streams.append((name,base[:n],base[n:]))
    for kib in ks:
        for name,learn,tail in streams:
            picks,aux=pick(d,kib,learn,len(tail));lm=aux['lm']
            with scope(d.cache):(z,zi),zs=timed(Z.select,d.s,d.scores,lm,kib,len(tail))
            ra,rs=picks['RA6'];bf,bs=picks['BF'];t=time.perf_counter()
            r,_=d.e.evaluate(ra,learn);b,_=d.e.evaluate(bf,learn);gate=bf if b[0]<=r[0] else ra;gate_extra=time.perf_counter()-t
            choices={m:picks[m] for m in ('Gama','Replay','RA6','BF')}
            choices.update({'RA6-Z-predictive':(z,zs+aux['summary_s']),'RA6-ZGate':(gate,rs+bs+gate_extra)})
            for m,(c,ts) in choices.items():rows.append(dict(dataset=ds,seed=seed,budget_kib=kib,workload=name,**result(d,c,tail,m,ts)))
            assert int(d.e.evaluate(gate,learn)[0][0])==min(int(r[0]),int(b[0]))
            cases.append(dict(budget_kib=kib,workload=name,learn_sha=ah(learn),tail_sha=ah(tail),learning_queries=len(learn),tail_queries=len(tail),predictive_info=zi,RA_learning_fp=int(r[0]),BF_learning_fp=int(b[0]),gate_trees=gate['trees']))
            print('ZERO_CASE',ds,seed,kib,name,'t0',z['trees'],gate['trees'],flush=True)
    save(ROOT/f'results/zero_{ds}_{seed}.json',dict(status='complete',meta=d.meta,cases=cases,rows=rows,wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss));check()


@njit(cache=True)
def cyclic(keys,counts):
    out=np.empty(counts.sum(),np.int64);remaining=counts.copy();active=keys.copy();idx=np.arange(len(keys));pos=0
    while len(idx):
        nxt=np.empty(len(idx),np.int64);n=0
        for j in idx:
            out[pos]=keys[j];pos+=1;remaining[j]-=1
            if remaining[j]>0:nxt[n]=j;n+=1
        idx=nxt[:n]
    return out


def permute(stream,mode):
    if mode=='original':return stream
    if mode=='shuffled':return np.random.default_rng(5401).permutation(stream)
    k,n=np.unique(stream,return_counts=True)
    return np.repeat(k,n) if mode=='bursty' else cyclic(k,n)


def coupled(ds):
    check();start=time.perf_counter();d=load(ds,3601 if ds=='clark' else 0);rows=[];cases=[];all_candidates=[];numerics=[]
    from mechanism54 import analyze
    for kib in CMATRIX[ds]:
        with scope(d.cache):
            (table,table_s)=timed(RA.candidate_table,d.s,d.scores,d.lm,kib,len(d.tail),RA.Config(new_mix=0.))
            def buildall():
                return [E5.build(d.s,d.scores,r['trees'],kib,r['frac'],weights=r['weights'],cache_bytes=r['cache_bytes'],slots=r['slots']) for r in table]
            weighted,weighted_build_s=timed(buildall)
            hgrid,hbuild_s=timed(E5.candidates,d.s,d.scores,kib)
            bgrid,bbuild_s=timed(lambda:[B.build(d.s,kib,f,d.cache) for f in E5.FRACS])
            # Independent frozen selector regression of the manually decomposed stages.
            (ra,ri),ra_s=timed(R6.select6,d.s,d.scores,d.lm,kib,len(d.tail))
        rank=sorted(range(len(table)),key=lambda i:(table[i]['pred'],table[i]['trees'],table[i]['frac']))
        stage1=weighted[rank[0]];refined=[]
        for r,i in enumerate(rank[:5]):
            c=weighted[i];pred=R6.bucket_prediction(d.s,d.lm,E5.tree(d.s,d.scores,c['trees']),c,len(d.tail),table[i]['seg_fpr_pred']);refined.append((pred,r,i))
        chosen=min(refined)[2];manual=weighted[chosen]
        assert (manual['trees'],manual['frac'],ah(manual['structure'].fp_static))==(ra['trees'],ra['frac'],ah(ra['structure'].fp_static))
        # Build/selection timings measured separately for Stage1; full grid not free.
        with scope(d.cache):
            _,stage1_build_s=timed(E5.build,d.s,d.scores,table[rank[0]]['trees'],kib,table[rank[0]]['frac'],weights=table[rank[0]]['weights'],cache_bytes=table[rank[0]]['cache_bytes'],slots=table[rank[0]]['slots'])
        g=E5.gama(hgrid)
        numerics.append(dict(dataset=ds,budget_kib=kib,**analyze(d,kib,g)))
        oldfreq_l=np.bincount(d.learn,minlength=len(d.qi));oldfreq_t=np.bincount(d.tail,minlength=len(d.qi))
        for mode in ('original','shuffled','bursty','cyclic'):
            (learn,tail),order_s=timed(lambda:(permute(d.learn,mode),permute(d.tail,mode)))
            assert np.array_equal(np.bincount(learn,minlength=len(d.qi)),oldfreq_l) and np.array_equal(np.bincount(tail,minlength=len(d.qi)),oldfreq_t)
            lm=summarize19(learn);assert ah(lm.keys)==ah(d.lm.keys) and ah(lm.counts)==ah(d.lm.counts) and ah(lm.rate)==ah(d.lm.rate)
            (rep,rl),rs=timed(d.e.best,hgrid,learn);(wrep,wl),ws=timed(d.e.best,weighted,learn);(bf,bl),bs=timed(d.e.best,bgrid,learn)
            (zrep,zl),zs=timed(d.e.best,weighted+bgrid,learn)
            choices={'Gama':(g,hbuild_s),'h-Replay':(rep,hbuild_s+rs),'RA-stage1':(stage1,table_s+stage1_build_s+d.meta['timings']['summary_s']),'RA-stage2':(ra,ra_s+d.meta['timings']['summary_s']),'weighted-Replay':(wrep,table_s+weighted_build_s+ws+d.meta['timings']['summary_s']),'BF':(bf,bbuild_s+bs),'weighted-ZReplay':(zrep,table_s+weighted_build_s+bbuild_s+zs+d.meta['timings']['summary_s'])}
            for m,(c,ts) in choices.items():rows.append(dict(dataset=ds,budget_kib=kib,order=mode,**result(d,c,tail,m,ts)))
            for i,c in enumerate(weighted):
                t=time.perf_counter();cnt,_=d.e.evaluate(c,tail)
                all_candidates.append(dict(dataset=ds,budget_kib=kib,order=mode,trees=c['trees'],frac=c['frac'],stage1_prediction=table[i]['pred'],tail_fp=int(cnt[0]),tail_replay_s=time.perf_counter()-t))
            cases.append(dict(budget_kib=kib,order=mode,learning_sha=ah(learn),tail_sha=ah(tail),histograms_equal=True,prediction_inputs_bit_equal=True,RA_stage2_fp=int(next(r['fp'] for r in reversed(rows) if r['method']=='RA-stage2')),candidate_count=len(weighted),weighted_build_s=weighted_build_s,table_s=table_s,order_generation_s=order_s,h_learning_candidates=rl,weighted_learning_candidates=wl,BF_learning_candidates=bl,union_learning_candidates=zl,top5=refined))
            print('ORDER_CASE',ds,kib,mode,'FP',[(r['method'],r['fp']) for r in rows[-7:]],flush=True)
    save(ROOT/f'results/coupled_{ds}.json',dict(status='complete',meta=d.meta,rows=rows,cases=cases,numerics=numerics,all_weighted_tail_candidates=all_candidates,wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss));check()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('zero','coupled'));p.add_argument('dataset');p.add_argument('--seed',type=int,default=0);a=p.parse_args()
    zero(a.dataset,a.seed) if a.mode=='zero' else coupled(a.dataset)

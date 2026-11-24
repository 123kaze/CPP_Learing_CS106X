"""Frozen-input, no-index method comparison. Selection is rerun under the full-key layout."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
from cache53 import Cache,Evaluator,layout_scope,member_hits,lookup,insert
import csv,resource


def ledger(c):
    s=c['structure']
    assert s.used_bytes==s.model_bytes+s.filter_bytes+s.metadata_bytes+s.array_overhead_bytes+c['cache_bytes']<=s.budget_bytes
    return dict(total_bytes=int(s.used_bytes),budget_bytes=int(s.budget_bytes),model_bytes=int(s.model_bytes),bf_bytes=int(s.filter_bytes),metadata_bytes=int(s.metadata_bytes),header_bytes=int(s.array_overhead_bytes),cache_bytes=int(c['cache_bytes']),cache_slots=int(c['slots']),required_member_index_bytes=0)


def reference(ds,kib):
    folder=WR/('round6_bucket/results/holdout/round5_methods' if ds=='mawi2024_flow' else 'round5_dp/results')
    with (folder/f'rows_{ds}_{kib}.csv').open() as f:
        return {(r['workload'],int(r['seed']),r['method']):r for r in csv.DictReader(f)}


def run(ds,kib,pilot=False):
    start=time.perf_counter();check_inputs(ds)
    name=('pilot_' if pilot else '')+f'{ds}_{kib}'
    dest=ROOT/f'results/{name}.json';assert not dest.exists()
    cache=Cache(width(ds));rows=[];work=[]
    with no_index(),layout_scope(cache):
        s,scores,blob,offsets,qi,mi,load_s=load(ds)
        evaluator=Evaluator(cache,s,blob,offsets,qi)
        t=time.perf_counter()
        for trees in E5.TREES:E5.tree(s,scores,trees)
        tree_s=time.perf_counter()-t
        # Compile/load kernels separately; not a re-training or end-to-end timing.
        t=time.perf_counter();spec=cache.layout(4096);data=cache.allocate(spec)
        insert(data,np.uint64(1),np.zeros(8,np.uint8),spec['buckets'],cache.width)
        lookup(data,np.uint64(1),np.zeros(8,np.uint8),spec['buckets'],cache.width)
        BF.build(s,kib,0,cache)
        warm=E5.build(s,scores,1,kib,0.)
        evaluator.evaluate(warm,np.zeros(1,np.int64))
        member_hits(data,s.h1m[:1],blob,offsets,mi[:1],spec['buckets'],cache.width)
        jit_s=time.perf_counter()-t
        t=time.perf_counter();grid=[];build_cost={}
        for trees in E5.TREES:
            for frac in E5.FRACS:
                bt=time.perf_counter();c=E5.build(s,scores,trees,kib,frac);elapsed=time.perf_counter()-bt
                if c is not None:grid.append(c);build_cost[trees,frac]=elapsed
        grid_s=time.perf_counter()-t;assert grid
        g=E5.gama(grid);by={(c['trees'],c['frac']):c for c in grid};g10=by[g['trees'],.1]
        g_s=sum(v for (tr,fr),v in build_cost.items() if fr==0.)
        t=time.perf_counter();bfgrid=[];bfcost={}
        for frac in E5.FRACS:
            bt=time.perf_counter();bfgrid.append(BF.build(s,kib,frac,cache));bfcost[frac]=time.perf_counter()-bt
        bfgrid_s=time.perf_counter()-t
        refs=reference(ds,kib)
        out=dict(status='running',pilot=pilot,dataset=ds,budget_kib=kib,seed=0,cache_schema_width=cache.width,members=len(s.h1m),negative_pool=len(s.h1q),input_load_s=load_s,shared_tree_preparation_s=tree_s,JIT_warm_s=jit_s,learned_grid_build_s=grid_s,bf_grid_build_s=bfgrid_s,candidates=len(grid),model_training='reused frozen model; not retimed',score_generation='reused frozen prefixes; not retimed',member_index_built=False,raw_key_blob_bytes=blob.nbytes,raw_key_offsets_bytes=offsets.nbytes,raw_key_array_header_bytes=sys.getsizeof(blob)-blob.nbytes+sys.getsizeof(offsets)-offsets.nbytes,member_hash_input_bytes=s.h1m.nbytes,query_hash_input_bytes=s.h1q.nbytes,all_ids_input_bytes=s.ids.nbytes,split_mask_bytes=sum(a.nbytes for a in s.split.values()),shared_tree_segment_bytes=sum(td.seg_m.nbytes+td.seg_q.nbytes for td in E5._TREE.values()),rows=rows,workloads=work)
        for wname,wsp in workloads(ds):
            wt=time.perf_counter();t=time.perf_counter();base=E5.base_stream(s,wname,wsp,0,10000000);stream_s=time.perf_counter()-t
            n=len(base)//4;learn,tail=base[:n],base[n:];assert n>0 and len(tail)>0
            t=time.perf_counter();lm=summarize19(learn);summary_s=time.perf_counter()-t
            t=time.perf_counter();rep,rep_log=evaluator.best(grid,learn);rep_s=time.perf_counter()-t
            t=time.perf_counter();glob,gi=RA.select(s,scores,lm,kib,len(tail),RA.Config(mode='global',new_mix=0.));glob_s=time.perf_counter()-t
            t=time.perf_counter();ra,ri=ra6.select6(s,scores,lm,kib,len(tail));ra_s=time.perf_counter()-t
            t=time.perf_counter();bf,bf_log=evaluator.best(bfgrid,learn);bf_s=time.perf_counter()-t
            chosen=[('Gama',g,g_s,{}),('Gama+10%',g10,g_s+build_cost[g['trees'],.1],{}),('Replay',rep,grid_s+rep_s,dict(learning_replay_s=rep_s,candidate_build_s=grid_s)),('RA-global',glob,glob_s+summary_s,gi),('RA-PLBF-GT19',ra,ra_s+summary_s,ri),('BF+Exact',bf,bfgrid_s+bf_s,dict(learning_replay_s=bf_s,candidate_build_s=bfgrid_s)),('PlainBF',bfgrid[0],bfcost[0.],{})]
            long=np.diff(offsets)[qi]>cache.width
            wm=dict(workload=wname,stream_sha256=ah(base),learning_sha256=ah(learn),tail_sha256=ah(tail),learning_queries=len(learn),tail_queries=len(tail),stream_generation_s=stream_s,summary_s=summary_s,learning_state_bytes=int(lm.state_bytes),learning_trace_bytes=learn.nbytes,full_trace_bytes=base.nbytes,query_keys_over_width=int(long.sum()),tail_requests_over_width=int(long[tail].sum()),replay_candidate_results=rep_log,bf_candidate_results=bf_log)
            for method,c,selection_s,info in chosen:
                t=time.perf_counter();cnt,state=evaluator.evaluate(c,tail);tail_s=time.perf_counter()-t
                assert cnt[5]==len(tail) and cnt[6]==0
                spec=cache.layout(c['cache_bytes']);before=ah(state)
                t=time.perf_counter();hits=int(member_hits(state,s.h1m,blob,offsets,mi,spec['buckets'],cache.width));member_s=time.perf_counter()-t
                assert hits==0 and ah(state)==before
                row=dict(dataset=ds,budget_kib=kib,workload=wname,seed=0,method=method,trees=c['trees'],frac=c['frac'],fp=int(cnt[0]),tail_queries=len(tail),cache_hits=int(cnt[1]),inserts=int(cnt[2]),evictions=int(cnt[3]),bypasses=int(cnt[4]),member_BF_FN=0,final_member_cache_hits=hits,cache_sha256=before,static_flags_sha256=ah(c['structure'].fp_static),selection_build_s=selection_s,tail_reference_replay_s=tail_s,all_member_cache_check_s=member_s,selection_info=info,**ledger(c))
                oldname={'Replay':'LearnGrid','RA-PLBF-GT19':'RA6'}.get(method,method)
                old=refs.get((wname,0,oldname))
                if old is not None:row['historical_prefix_fp']=int(old['fp_tail'])
                if method=='Gama':
                    assert old is not None and row['fp']==int(old['fp_tail']) and row['trees']==int(old['trees'])
                    row['Gama_old_FP_regression']=True
                rows.append(row);print('ROW',name,wname,method,'FP',row['fp'],'BYTES',row['total_bytes'],flush=True)
            wm['wall_s']=time.perf_counter()-wt;work.append(wm);save(dest,out)
        assert len(rows)==len(workloads(ds))*len(METHODS)
        assert not hasattr(s,'member_hashes') and not hasattr(s,'cache_cost')
    check_sources();out.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    assert out['peak_rss_bytes']<4*1024**3;save(dest,out)
    print('WORKER_COMPLETE',name,round(out['wall_s'],3),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=DATASETS);p.add_argument('kib',type=int);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    assert a.kib in BUDGETS[a.dataset]
    try:run(a.dataset,a.kib,a.pilot)
    except Exception as e:save(ROOT/f'results/{"pilot_" if a.pilot else ""}{a.dataset}_{a.kib}.failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:500]));raise

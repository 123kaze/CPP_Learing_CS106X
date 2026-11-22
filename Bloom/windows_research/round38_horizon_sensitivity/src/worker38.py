import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from horizon38 import *
from types import SimpleNamespace
import csv,resource


def input_paths(ds,seed):
    if ds=='clarknet':
        return [WR/'round36_http_qualification/cache/clarknet.npz',WR/'round36_http_qualification/results/clarknet.json',
                WR/f'round37_clarknet_controls/results/seed{seed}.json']
    folder=E5.C.CACHE/ds
    paths=[folder/p for p in ('data.npz','scores.npz','gama_scores.npz','model200.txt')]
    if ds.endswith('_flow'):paths.append(folder/'trace.npy')
    return paths


def prepare(ds,seed,mode):
    if ds.endswith('_tcp_flow'):
        sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p in input_paths(ds,seed):assert sha(p)==freeze['inputs'][str(p.relative_to(BLOOM))],p
    timings={};start=time.perf_counter()
    if ds=='clarknet':
        s,X,learn,tail=W.prepare(input_paths(ds,seed)[0],seed)
        timings['input_and_stream_preparation_s']=time.perf_counter()-start
        train=s.split['member_train']|s.split['neg_train'];t=time.perf_counter()
        model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,
                              deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[train],label=s.y[train]),num_boost_round=200)
        timings['model_training_s']=time.perf_counter()-t;assert model.num_trees()==200
        t=time.perf_counter();scores=W.prefix_raw_scores(model,X,E5.TREES)
        for trees in E5.TREES:
            assert np.array_equal(scores[trees],model.predict(X,raw_score=True,num_iteration=trees,num_threads=1))
        timings['score_preparation_and_verification_s']=time.perf_counter()-t
        s.q_score=scores[200][s.split['neg_test']]
        old=json.loads((WR/f'round37_clarknet_controls/results/seed{seed}.json').read_text())
        assert W.ah(learn)==old['learning_sha256'] and W.ah(tail)==old['tail_sha256']
        held=(s.y&~s.split['member_train'])|s.split['neg_val']
        assert np.isclose(W.auc(s.y[held],scores[16][held]),old['development_auc16'],atol=1e-12,rtol=0)
        del X
    else:
        folder=E5.C.CACHE/ds
        with np.load(folder/'data.npz',allow_pickle=False) as f:ids,y=f['ids'],f['y']
        with np.load(folder/'scores.npz',allow_pickle=False) as f:score48=f['score']
        sp=E5.C.make_split(ids,y,ds);hashes=E5.C.splitmix64(ids^np.uint64(E5.C.H1_SALT))
        s=SimpleNamespace(name=ds,ids=ids,y=y,split=sp,h1m=hashes[y],h1q=hashes[sp['neg_test']],
                          q_ids=ids[sp['neg_test']],q_score=score48[sp['neg_test']])
        scores=E5.R.scores_for(s);model=W.lgb.Booster(model_file=str(folder/'model200.txt'))
        timings['prepared_data_model_loading_s']=time.perf_counter()-start;timings['model_training_s']=0.
        t=time.perf_counter();workload='真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部'
        spec=None if ds.endswith('_flow') else dict(E5.workload_specs(len(s.h1q)))[workload]
        base=E5.base_stream(s,workload,spec,seed,10000000);cut=len(base)//4;learn,tail=base[:cut],base[cut:]
        timings['stream_preparation_s']=time.perf_counter()-t
    t=time.perf_counter()
    for trees in E5.TREES:
        E5.R._MODEL_ARRAYS[s.name,trees]=W.model_arrays(model,trees)
        E5.tree(s,scores,trees)
    timings['model_arrays_and_segment_statistics_s']=time.perf_counter()-t
    t=time.perf_counter();safe=None;index_payload=index_physical=0
    if mode=='index':
        s.member_hashes=np.sort(s.h1m);safe=E5.E.CC.safe_prefix_lengths(s.member_hashes,s.h1q)
        index_payload=s.member_hashes.nbytes;index_physical=sys.getsizeof(s.member_hashes)
    else:assert not hasattr(s,'member_hashes')
    timings['index_and_safe_prefix_preparation_s']=time.perf_counter()-t
    t=time.perf_counter();lm=W.summarize19(learn);timings['GT_summary_s']=time.perf_counter()-t
    assert len(learn)>0 and len(tail)>0
    t=time.perf_counter();cache=CACHES[mode];sp=cache.layout(512);data=cache.allocate(sp)
    aux=safe[:0] if mode=='index' else np.empty(0,np.bool_)
    cache.replay(np.empty(0,np.int64),s.h1q[:0],aux,np.empty(0,np.bool_),data,sp['buckets'],sp['prefix_bits'],sp['Q'],sp['ob'],sp['slot_bits'],4,sp['handbits'],2**62,np.empty(0,np.int64),np.empty(0,np.bool_))
    cache.count_member_hits(data,s.h1m[:0],sp['buckets'],sp['prefix_bits'],sp['Q'],sp['ob'],sp['slot_bits'],4)
    E5.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.)
    E5.R.packed_build(s.h1m[:0],np.empty(0,np.int32),np.array([0,8],np.int64),np.array([8],np.int64),np.array([1],np.int64),np.zeros(1,np.uint8))
    E5.R.packed_query(s.h1m[:0],np.empty(0,np.int32),np.array([E5.C.BF],np.uint8),np.array([0,8],np.int64),np.array([8],np.int64),np.array([1],np.int64),np.zeros(1,np.uint8))
    timings['JIT_warm_s']=time.perf_counter()-t
    return s,scores,safe,learn,tail,lm,dict(timings=timings,backend_index_payload_bytes=index_payload,
        backend_index_physical_bytes=index_physical,retains_sorted_member_index=hasattr(s,'member_hashes'),
        members=len(s.h1m),negative_pool=len(s.h1q),learning_queries=len(learn),actual_H=len(tail),
        learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),rate_sha256=W.ah(lm.rate),
        member_hashes_sha256=W.ah(s.h1m),negative_hashes_sha256=W.ah(s.h1q))


def check_reference(ds,seed,kib,mode,row,meta):
    if ds=='clarknet':
        if mode=='fp64':return 'new fp64 matched-H result; not a pre-existing holdout'
        old=json.loads((WR/f'round37_clarknet_controls/results/seed{seed}.json').read_text())
        ref=next(r for r in old['rows'] if r['budget_kib']==kib and r['method']=='RA-PLBF-GT19')
        assert (row['fp'],row['trees'],row['frac'],row['cache_bytes'],row['static_flags_sha256'])==(ref['fp'],ref['trees'],ref['cache_frac'],ref['cache_physical_bytes'],ref['static_flags_sha256'])
        assert meta['tail_sha256']==old['tail_sha256']
        return 'round37 configuration, FP and full-pool flags reproduced'
    with (WR/'round19_gt_fix/results/updated_main_comparisons.csv').open() as f:
        expected=[r for r in csv.DictReader(f) if r['dataset']==ds and int(r['budget_kib'])==kib and int(r['seed'])==seed and r['cache']==mode and r['workload']==('真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部')]
    assert len(expected)==1
    assert row['fp']==int(expected[0]['repaired_ra_fp']),(ds,kib,mode,row['fp'],expected[0]['repaired_ra_fp'])
    return 'round19 repaired/unchanged-input archived FP reproduced'


def run(ds,seed,mode):
    start=time.perf_counter();frozen=check_freeze();E5.K=CACHES[mode]
    assert W.get_num_threads()==1
    output=ROOT/f'results/{ds}_{seed}_{mode}.json';assert not output.exists(),'Refuse overwrite'
    s,scores,safe,learn,tail,lm,meta=prepare(ds,seed,mode)
    selected=[r for r in cases() if r['dataset']==ds and r['seed']==seed];assert selected
    result=dict(status='running',dataset=ds,seed=seed,cache=mode,freeze_sha256=frozen,native_threads=1,**meta,cases=[])
    options=horizons(len(learn),len(tail));original_rates=lm.rate.copy()
    for case in selected:
        kib=case['budget_kib'];index=cases().index(case);order=rule_order(index+(1 if mode=='fp64' else 0))
        item=dict(**case,cache=mode,rule_order=list(order),rows={});arrays={};states={}
        for rule in order:
            h=options[rule];c,info=select(s,scores,lm,kib,h)
            assert np.array_equal(lm.rate.view(np.uint8),original_rates.view(np.uint8))
            t=time.perf_counter();p,a=payload(s,scores,c);payload_s=time.perf_counter()-t
            counts,state=evaluate(c,tail,s,safe,mode);st=c['structure']
            assert st.used_bytes==st.model_bytes+st.metadata_bytes+st.array_overhead_bytes+st.filter_bytes+c['cache_bytes']<=kib*1024
            item['rows'][rule]=dict(rule=rule,assumed_H=h,actual_H=len(tail),assumed_over_actual=h/len(tail),actual_over_assumed=len(tail)/h,
                trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes'],slots=c['slots'],total_bytes=st.used_bytes,
                model_payload_bytes=st.model_bytes,metadata_bytes=st.metadata_bytes,array_header_bytes=st.array_overhead_bytes,bf_payload_bytes=st.filter_bytes,
                **counts,payload=p,payload_check_s=payload_s,selection_info=info,static_flags_sha256=W.ah(st.fp_static))
            arrays[rule]=a;states[rule]=state
            W.save(output,dict(**result,in_progress_case=item))
            print('H_RULE',ds,seed,mode,kib,rule,'H',h,'FP',counts['fp'],'trees',c['trees'],'frac',c['frac'],flush=True)
        ref=item['rows']['matched'];ranking={(r['trees'],r['frac']):r['rank'] for r in ref['selection_info']['table']}
        old_top={k for k,r in ranking.items() if r<5}
        for rule,row in item['rows'].items():
            rank={(r['trees'],r['frac']):r['rank'] for r in row['selection_info']['table']};assert rank.keys()==ranking.keys()
            same=arrays_equal(arrays[rule],arrays['matched']) and row['cache_bytes']==ref['cache_bytes'] and row['total_bytes']==ref['total_bytes']
            same_cache=states[rule].dtype==states['matched'].dtype and states[rule].shape==states['matched'].shape and np.array_equal(states[rule].view(np.uint8),states['matched'].view(np.uint8))
            if row['assumed_H']==ref['assumed_H']:assert same and same_cache and row['fp']==ref['fp']
            if same:assert same_cache and row['fp']==ref['fp']
            row.update(same_configuration_as_matched=(row['trees'],row['cache_bytes'])==(ref['trees'],ref['cache_bytes']),
                       payload_byte_equal_matched=same,cache_byte_equal_matched=same_cache,fp_ratio_to_matched=(row['fp']+1)/(ref['fp']+1),
                       rank_positions_changed=sum(rank[k]!=ranking[k] for k in rank),top5_overlap=len(old_top&{k for k,r in rank.items() if r<5}))
        item['reference_verification']=check_reference(ds,seed,kib,mode,ref,meta)
        result['cases'].append(item);W.save(output,result)
    check_freeze();result.update(status='complete',wall_s=time.perf_counter()-start,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
    W.save(output,result);print('COMPLETE_WORKER',ds,seed,mode,len(selected)*4,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('seed',type=int);p.add_argument('cache',choices=CACHES);a=p.parse_args()
    try:run(a.dataset,a.seed,a.cache)
    except Exception as e:
        W.save(ROOT/f'results/{a.dataset}_{a.seed}_{a.cache}.failure.json',dict(status='failed',error=repr(e)))
        raise

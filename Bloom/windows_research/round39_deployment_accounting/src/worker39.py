"""Learning-to-tail count replay; not a new database latency benchmark."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(WR/'round38_horizon_sensitivity/src'))
import horizon38 as H
from account39 import calls,project,required_index_bytes,SCENARIOS
from types import SimpleNamespace
import csv,hashlib,json,time,resource
np=H.np;W=H.W;E5=H.E5;CACHES=H.CACHES


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['sources'].items():assert sha(BLOOM/p)==h,p
    return sha(ROOT/'plan/freeze.json')


def archive_file(ds,kib,mode):
    base=WR/'round12_nomodel/results/main' if ds in ('cod','url','shalla') or ds.endswith('_tcp_flow') else WR/'round13_complete/results/baselines'
    return base/mode/f'rows_{ds}_{kib}.csv'


def paths(ds,seed,mode):
    result=[WR/f'round38_horizon_sensitivity/results/{ds}_{seed}_{mode}.json']
    if ds=='clarknet':
        result += [WR/'round36_http_qualification/cache/clarknet.npz',WR/f'round37_clarknet_controls/results/seed{seed}.json']
    else:
        folder=E5.C.CACHE/ds
        result += [folder/'data.npz',folder/'scores.npz']
        if ds.endswith('_flow'):result.append(folder/'trace.npy')
        result += [archive_file(ds,c['budget_kib'],mode) for c in H.cases() if c['dataset']==ds and c['seed']==seed]
        result.append(WR/'round13_complete/results/combined_baseline_rows.csv')
    return result


def prepare(ds,seed,mode):
    if ds.endswith('_tcp_flow'):
        sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
    t=time.perf_counter();freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p in paths(ds,seed,mode):assert sha(p)==freeze['inputs'][str(p.relative_to(BLOOM))],p
    times={'input_hash_verification_s':time.perf_counter()-t};start=time.perf_counter()
    if ds=='clarknet':
        s,X,learn,tail=W.prepare(WR/'round36_http_qualification/cache/clarknet.npz',seed)
        del X
        full_hash=None
    else:
        folder=E5.C.CACHE/ds
        with np.load(folder/'data.npz',allow_pickle=False) as f:ids,y=f['ids'],f['y']
        with np.load(folder/'scores.npz',allow_pickle=False) as f:score=f['score']
        split=E5.C.make_split(ids,y,ds);hashes=E5.C.splitmix64(ids^np.uint64(E5.C.H1_SALT))
        s=SimpleNamespace(name=ds,ids=ids,y=y,split=split,h1m=hashes[y],h1q=hashes[split['neg_test']],q_score=score[split['neg_test']])
        workload='真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部'
        spec=None if ds.endswith('_flow') else dict(E5.workload_specs(len(s.h1q)))[workload]
        base=E5.base_stream(s,workload,spec,seed,10000000);cut=len(base)//4;learn,tail=base[:cut],base[cut:];full_hash=W.ah(base)
    times['data_hash_and_stream_preparation_s']=time.perf_counter()-start
    t=time.perf_counter();prior=json.loads((WR/f'round38_horizon_sensitivity/results/{ds}_{seed}_{mode}.json').read_text())
    assert W.ah(learn)==prior['learning_sha256'] and W.ah(tail)==prior['tail_sha256']
    times['matched_reference_and_stream_check_s']=time.perf_counter()-t
    t=time.perf_counter();lm=W.summarize19(learn)
    state_memory=dict(distinct_learning_keys=len(lm.keys),learning_queries=len(learn),distinct_fraction=len(lm.keys)/len(learn),
        retained_trace_payload_bytes=learn.nbytes,counts_only_payload_bytes=lm.state_bytes,
        keys_counts_rates_payload_bytes=lm.keys.nbytes+lm.counts.nbytes+lm.rate.nbytes,
        counts_payload_over_trace=lm.state_bytes/learn.nbytes,
        summary_payload_over_trace=(lm.keys.nbytes+lm.counts.nbytes+lm.rate.nbytes)/learn.nbytes,
        arrays_own_data=[bool(a.flags.owndata) for a in (lm.keys,lm.counts,lm.rate)])
    times['GT_summary_for_memory_accounting_s']=time.perf_counter()-t
    del lm
    t=time.perf_counter()
    # A finite-domain check for this accounting identity, not a universal hash guarantee.
    assert not np.intersect1d(s.h1m,s.h1q).size,'Member/nonmember fingerprint collision: positive-call cancellation not established'
    times['finite_hash_disjointness_check_s']=time.perf_counter()-t
    safe=None;index_s=prefix_s=0.
    if mode=='index':
        t=time.perf_counter();s.member_hashes=np.sort(s.h1m);index_s=time.perf_counter()-t
        t=time.perf_counter();safe=E5.E.CC.safe_prefix_lengths(s.member_hashes,s.h1q);prefix_s=time.perf_counter()-t
    else:assert not hasattr(s,'member_hashes')
    times['member_index_sort_s']=index_s;times['all_pool_safe_prefix_precompute_s']=prefix_s
    return s,learn,tail,safe,prior,dict(timings=times,learning_state_memory=state_memory,base_stream_sha256=full_hash,learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),
        learning_queries=len(learn),tail_queries=len(tail),members=len(s.h1m),array_header_bytes=sys.getsizeof(np.empty(0,np.uint64)),
        actual_sorted_index_payload_bytes=8*len(s.h1m) if mode=='index' else 0,
        retains_sorted_member_index=hasattr(s,'member_hashes'),finite_fingerprints_disjoint=True)


def replay(c,stream,s,safe,mode,data=None):
    cache=CACHES[mode];sp=cache.layout(c['cache_bytes'])
    if data is None:data=cache.allocate(sp)
    aux=safe if mode=='index' else np.empty(0,np.bool_)
    t=time.perf_counter()
    count=cache.replay(stream,s.h1q,aux,c['structure'].fp_static,data,sp['buckets'],sp['prefix_bits'],sp['Q'],sp['ob'],sp['slot_bits'],4,sp['handbits'],2**62,np.empty(0,np.int64),np.empty(0,np.bool_))
    elapsed=time.perf_counter()-t;assert count[5]==len(stream) and count[6]==0
    t=time.perf_counter();fn=int(cache.count_member_hits(data,s.h1m,sp['buckets'],sp['prefix_bits'],sp['Q'],sp['ob'],sp['slot_bits'],4))
    member_check_s=time.perf_counter()-t;assert fn==0,'Finite dataset cache check failed'
    return dict(fp=int(count[0]),hits=int(count[1]),processed=int(count[5]),member_cache_hits=fn,cache_sha256=W.ah(data),
                replay_s=elapsed,member_check_s=member_check_s),data


def resource_row(st,cache_bytes,mode,members,header):
    index=required_index_bytes(mode,cache_bytes,members,header)
    return dict(filter_actual_bytes=int(st.used_bytes),cache_bytes=int(cache_bytes),required_index_if_absent_bytes=index,
                additional_index_if_already_available_bytes=0,filter_plus_required_index_bytes=int(st.used_bytes)+index)


def resource_archive(row,mode,members,header):
    used=int(row['total_bytes']);cb=int(row['cache_alloc_bytes']);index=required_index_bytes(mode,cb,members,header)
    assert used==sum(int(row[k]) for k in ('bf_bytes','metadata_bytes','overhead_bytes','cache_alloc_bytes'))
    return dict(filter_actual_bytes=used,cache_bytes=cb,required_index_if_absent_bytes=index,
                additional_index_if_already_available_bytes=0,filter_plus_required_index_bytes=used+index)


def run(ds,seed,mode):
    start=time.perf_counter();frozen=check();E5.K=CACHES[mode];assert W.get_num_threads()==1
    out=ROOT/f'results/{ds}_{seed}_{mode}.json';assert not out.exists(),'Refuse overwrite'
    s,learn,tail,safe,prior,meta=prepare(ds,seed,mode)
    result=dict(status='running',dataset=ds,seed=seed,cache=mode,freeze_sha256=frozen,**meta,cases=[])
    # Compile shared scalar signatures before timing the case-specific BF builds/replays.
    t=time.perf_counter();toy=W.B.build(s,4,0.,CACHES[mode]);replay(toy,learn[:0],s,safe,mode)
    result['JIT_warm_s']=time.perf_counter()-t;del toy
    for case in [r for r in H.cases() if r['dataset']==ds and r['seed']==seed]:
        kib=case['budget_kib'];old=next(c for c in prior['cases'] if c['budget_kib']==kib);ra=old['rows']['matched']
        baselines={};cold_selected=None;archive_check_s=0.
        if ds!='clarknet':
            archive_start=time.perf_counter()
            with archive_file(ds,kib,mode).open() as f:
                rr={r['method']:r for r in csv.DictReader(f) if r['workload']==case['workload'] and int(r['seed'])==seed}
            suffix='' if mode=='index' else '-fp64';plain=rr['BF'+suffix];chosen=rr['BF+ReplayCache'+suffix]
            for r in (plain,chosen):
                assert r['base_stream_sha256']==meta['base_stream_sha256'] and r['tail_stream_sha256']==meta['tail_sha256']
                assert int(r['learning_queries'])==len(learn) and int(r['tail_len'])==len(tail)
            baselines['plain']=dict(provenance='archived verified BF; not rebuilt this round',learning_fp=int(plain['learn_fp']),tail_fp=int(plain['fp_tail']),
                                   resources=resource_archive(plain,mode,len(s.h1m),meta['array_header_bytes']))
            cold_selected=dict(provenance='archived learning-selected BF+Cache; cold tail',tail_fp=int(chosen['fp_tail']),
                               frac=float(chosen['frac']),resources=resource_archive(chosen,mode,len(s.h1m),meta['array_header_bytes']))
            with (WR/'round13_complete/results/combined_baseline_rows.csv').open() as f:
                matched=[r for r in csv.DictReader(f) if r['dataset']==ds and int(r['budget_kib'])==kib and int(r['seed'])==seed and r['cache']==mode and r['workload']==case['workload']]
            assert len(matched)==1
            assert int(matched[0]['bf_fp'])==baselines['plain']['tail_fp'] and int(matched[0]['bfcache_fp'])==cold_selected['tail_fp']
            archive_check_s=time.perf_counter()-archive_start
        else:
            t=time.perf_counter();plain=W.B.build(s,kib,0.,CACHES[mode]);build_s=time.perf_counter()-t
            t=time.perf_counter();lfp=int(plain['structure'].fp_static[learn].sum());tfp=int(plain['structure'].fp_static[tail].sum());count_s=time.perf_counter()-t
            baselines['plain']=dict(provenance='new no-cache BF counts on unchanged ClarkNet stream',learning_fp=lfp,tail_fp=tfp,build_s=build_s,count_s=count_s,
                                   resources=resource_row(plain['structure'],0,mode,len(s.h1m),meta['array_header_bytes']))
            t=time.perf_counter();candidates=[W.B.build(s,kib,f,CACHES[mode]) for f in E5.FRACS];build_grid_s=time.perf_counter()-t
            t=time.perf_counter();best,_=E5.replay_best(candidates,learn,s,safe);selection_s=time.perf_counter()-t
            counts,_=replay(best,tail,s,safe,mode)
            if mode=='index':
                archive_start=time.perf_counter()
                ref=json.loads((WR/f'round37_clarknet_controls/results/seed{seed}.json').read_text())
                match=next(r for r in ref['rows'] if r['budget_kib']==kib and r['method']=='BF+Cache')
                assert counts['fp']==match['fp'] and best['frac']==match['cache_frac']
                archive_check_s=time.perf_counter()-archive_start
            cold_selected=dict(provenance='new BF+Cache selection on same learning stream; index reproduces round37',tail_fp=counts['fp'],frac=best['frac'],
                               build_grid_s=build_grid_s,selection_s=selection_s,counts=counts,
                               resources=resource_row(best['structure'],best['cache_bytes'],mode,len(s.h1m),meta['array_header_bytes']))
        t=time.perf_counter();fixed=W.B.build(s,kib,.1,CACHES[mode]);build_s=time.perf_counter()-t
        learn_counts,state=replay(fixed,learn,s,safe,mode)
        learned_state_sha=learn_counts['cache_sha256'];tail_counts,after=replay(fixed,tail,s,safe,mode,state)
        assert after is state
        baselines['fixed10']=dict(provenance='new predeclared 10% cache; state carried learning to tail',frac=.1,learning_fp=learn_counts['fp'],tail_fp=tail_counts['fp'],
                                  build_s=build_s,learning_counts=learn_counts,tail_counts=tail_counts,tail_start_cache_sha256=learned_state_sha,
                                  resources=resource_row(fixed['structure'],fixed['cache_bytes'],mode,len(s.h1m),meta['array_header_bytes']))
        comparisons=[]
        for name,baseline,shared in (('ready_plain',baselines['plain'],False),('ready_fixed10',baselines['fixed10'],False),('shared_labels_selected_cache',cold_selected,True)):
            b_learn=len(learn) if shared else baseline['learning_fp']
            accounting=calls(len(learn),len(tail),b_learn,baseline['tail_fp'],ra['fp'],shared)
            assert accounting['net_backend_calls_saved_after_one_window']==(b_learn+baseline['tail_fp'])-(len(learn)+ra['fp'])
            scenarios=[dict(**p,**project(accounting,**{k:v for k,v in p.items() if k!='name'})) for p in SCENARIOS]
            comparisons.append(dict(comparison=name,baseline_learning_backend_calls=b_learn,baseline_tail_backend_calls=baseline['tail_fp'],ra_tail_backend_calls=ra['fp'],
                                    **accounting,scenarios=scenarios))
        ra_index=required_index_bytes(mode,ra['cache_bytes'],len(s.h1m),meta['array_header_bytes'])
        item=dict(**case,cache=mode,RA_matched_fp=ra['fp'],RA_resources=dict(filter_actual_bytes=ra['total_bytes'],cache_bytes=ra['cache_bytes'],
                  required_index_if_absent_bytes=ra_index,additional_index_if_already_available_bytes=0,filter_plus_required_index_bytes=ra['total_bytes']+ra_index),
                  baselines=baselines,selected_cold_baseline=cold_selected,comparisons=comparisons,archived_baseline_verification_s=archive_check_s)
        assert all(b['resources']['filter_actual_bytes']<=kib*1024 for b in (*baselines.values(),cold_selected))
        result['cases'].append(item);W.save(out,result)
        print('ACCOUNT39',ds,seed,mode,kib,[(r['comparison'],r['extra_learning_backend_calls'],r['tail_backend_calls_saved']) for r in comparisons],flush=True)
    check();result.update(status='complete',wall_s=time.perf_counter()-start,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
    W.save(out,result);print('COMPLETE_ACCOUNT39',ds,seed,mode,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('seed',type=int);p.add_argument('cache',choices=CACHES);a=p.parse_args()
    try:run(a.dataset,a.seed,a.cache)
    except Exception as e:
        W.save(ROOT/f'results/{a.dataset}_{a.seed}_{a.cache}.failure.json',dict(status='failed',error=repr(e)))
        raise

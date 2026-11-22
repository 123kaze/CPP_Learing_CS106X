"""Sequential exact-key and full-auxiliary-budget experiment; all tail results retained."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from exact41 import *
from data41 import INPUT,OUTPUT,check
from types import SimpleNamespace
import time,json,resource
SEEDS=(3601,3602,3603);BUDGETS=(8,16,32)


def bf_build(s,budget,frac,cache):
    started=time.perf_counter();budget=int(budget);sp=cache.layout(int(budget*frac));cb=sp['allocated_bytes'] if frac else 0
    data=B.allocate(len(s.h1m),budget,cb);B.insert_all(data,s.h1m)
    assert B.query_all(data,s.h1m).all()
    flags=B.query_all(data,s.h1q);m,k=int(data[1]),int(data[2]);fpr=(-np.expm1(-k*len(s.h1m)/m))**k
    st=SimpleNamespace(trees=0,data=data,fp_static=flags,est_fpr=float(fpr),model_bytes=0,metadata_bytes=B.HEAD_WORDS*8,array_overhead_bytes=B.ARRAY_HEADER,filter_bytes=m//8,used_bytes=sys.getsizeof(data)+cb,budget_bytes=budget)
    return dict(trees=0,frac=float(frac),cache_bytes=cb,slots=sp['slots'] if cb else 0,structure=st,individual_build_s=time.perf_counter()-started)


def ledger(c,index_bytes=0):
    st=c['structure']
    assert st.used_bytes==st.model_bytes+st.metadata_bytes+st.array_overhead_bytes+st.filter_bytes+c['cache_bytes']<=st.budget_bytes
    return dict(filter_bytes=int(st.used_bytes),model_payload_bytes=int(st.model_bytes),bf_payload_bytes=int(st.filter_bytes),routing_bytes=int(st.metadata_bytes),header_bytes=int(st.array_overhead_bytes),cache_physical_bytes=int(c['cache_bytes']),cache_slots=int(c['slots']),required_extra_index_bytes=int(index_bytes),auxiliary_total_bytes=int(st.used_bytes+index_bytes))


def run(seed):
    frozen=check();outpath=ROOT/f'results/seed{seed}.json';assert not outpath.exists();start=time.perf_counter()
    rawmeta=json.loads((ROOT/'results/raw_key_verification.json').read_text());assert W.sha(OUTPUT)==rawmeta['sha256']
    t=time.perf_counter();s,X,learn,tail=W.prepare(INPUT,seed);sp=s.split
    with np.load(OUTPUT,allow_pickle=False) as d:blob,offsets=d['blob'],d['offsets']
    keys=[blob[offsets[i]:offsets[i+1]].tobytes() for i in range(len(s.ids))]
    qblob,qoffsets=pack([keys[i] for i in np.flatnonzero(sp['neg_test'])]);del keys
    with np.load(INPUT,allow_pickle=False) as d:trace,order,boundary=d['trace'],d['order'],int(d['boundary'])
    keep=(s.y|sp['neg_test'])[trace];mixed=trace[keep&(order>=boundary)].copy()
    hashes=E5.C.splitmix64(s.ids^np.uint64(E5.C.H1_SALT)^np.uint64(seed));memberidx=np.flatnonzero(s.y)
    assert np.array_equal(hashes[s.y],s.h1m) and np.array_equal(hashes[sp['neg_test']],s.h1q)
    prep_s=time.perf_counter()-t
    t=time.perf_counter();train=sp['member_train']|sp['neg_train']
    model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[train],label=s.y[train]),num_boost_round=200)
    train_s=time.perf_counter()-t;assert model.num_trees()==200
    t=time.perf_counter();scores=W.prefix_raw_scores(model,X,E5.TREES)
    for trees in E5.TREES:E5.R._MODEL_ARRAYS[s.name,trees]=W.model_arrays(model,trees)
    score_s=time.perf_counter()-t
    t=time.perf_counter()
    for trees in E5.TREES:E5.tree(s,scores,trees)
    tree_prepare_s=time.perf_counter()-t
    t=time.perf_counter();member_index=np.sort(s.h1m);safe=E5.E.CC.safe_prefix_lengths(member_index,s.h1q);index_s=time.perf_counter()-t
    index_bytes=sys.getsizeof(member_index)
    t=time.perf_counter();lm=W.summarize19(learn);summary_s=time.perf_counter()-t
    t=time.perf_counter();warm=bf_build(s,4096,.2,sys.modules['exact41']);evaluate(warm,learn[:2],s,qblob,qoffsets)
    spec=layout(warm['cache_bytes']);member_hits(allocate(spec),hashes,blob,offsets,memberidx[:1],spec['buckets'])
    W.evaluate(B.build(s,4,.1,K),learn[:2],s,safe);E5.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.)
    jit_s=time.perf_counter()-t
    old=json.loads((WR/f'round37_clarknet_controls/results/seed{seed}.json').read_text())
    assert W.ah(learn)==old['learning_sha256'] and W.ah(tail)==old['tail_sha256']
    out=dict(status='running',seed=seed,freeze_sha256=frozen,members=len(s.h1m),negative_pool=len(s.h1q),learning_queries=len(learn),tail_negative_queries=len(tail),mixed_tail_queries=len(mixed),mixed_tail_member_queries=int(s.y[mixed].sum()),learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),mixed_tail_sha256=W.ah(mixed),input_preparation_s=prep_s,model_training_s=train_s,score_preparation_s=score_s,shared_tree_preparation_s=tree_prepare_s,index_preparation_s=index_s,summary_s=summary_s,jit_warm_s=jit_s,index_bytes=index_bytes,rows=[])
    def exact_row(method,c,kib,selection_s,selection_extra=None,ceiling=None):
        t=time.perf_counter();fp,data,cnt=evaluate(c,tail,s,qblob,qoffsets);negative_s=time.perf_counter()-t
        spec=layout(c['cache_bytes']);before=W.ah(data)
        hits=int(member_hits(data,hashes,blob,offsets,memberidx,spec['buckets']));assert hits==0 and before==W.ah(data)
        flags=np.ones(len(s.ids),np.bool_);flags[sp['neg_test']]=c['structure'].fp_static
        t=time.perf_counter();mixed_data=allocate(spec);mcnt=replay(mixed,hashes,blob,offsets,flags,s.y,mixed_data,spec['buckets']);mixed_s=time.perf_counter()-t
        assert mcnt[4]==0 and mcnt[2]==out['mixed_tail_member_queries'] and mcnt[1]==fp,'Exact cache should be unaffected by nonmatching member interleaving'
        assert W.ah(data)==W.ah(mixed_data)
        assert int(member_hits(mixed_data,hashes,blob,offsets,memberidx,spec['buckets']))==0
        row=dict(method=method,format='exact128' if c['cache_bytes'] else 'no_cache',base_budget_kib=kib,auxiliary_ceiling_bytes=ceiling or kib*1024,trees=c['trees'],cache_frac=c['frac'],fp=fp,mixed_backend_calls=int(mcnt[0]),mixed_member_fn=int(mcnt[4]),final_member_cache_hits=hits,cache_sha256=before,flags_sha256=W.ah(c['structure'].fp_static),selection_s=selection_s,negative_replay_s=negative_s,mixed_replay_s=mixed_s,selection_extra=selection_extra or {},**ledger(c))
        assert row['auxiliary_total_bytes']<=row['auxiliary_ceiling_bytes']
        out['rows'].append(row);print('EXACT',seed,kib,method,'FP',fp,'bytes',row['auxiliary_total_bytes'],flush=True)
    for kib in BUDGETS:
        with exact_layout():
            t=time.perf_counter();g=E5.gama(E5.candidates(s,scores,kib,fracs=(0.,)));g_s=time.perf_counter()-t
            t=time.perf_counter();cands=E5.candidates(s,scores,kib);grid_s=time.perf_counter()-t
            t=time.perf_counter();rep,_=replay_best(cands,learn,s,qblob,qoffsets);replay_s=time.perf_counter()-t
            t=time.perf_counter();glob,gi=RA.select(s,scores,lm,kib,len(tail),RA.Config(mode='global',new_mix=0.));global_s=time.perf_counter()-t
            t=time.perf_counter();ra,ri=R6.select6(s,scores,lm,kib,len(tail));ra_s=time.perf_counter()-t
            t=time.perf_counter();bfcands=[bf_build(s,kib*1024,f,sys.modules['exact41']) for f in E5.FRACS];bf,bf_lfp=replay_best(bfcands,learn,s,qblob,qoffsets);bf_s=time.perf_counter()-t
            t=time.perf_counter();ra_lfp,_,_=evaluate(ra,learn,s,qblob,qoffsets);gate=bf if bf_lfp<=ra_lfp else ra;gate_s=time.perf_counter()-t
            for method,c,tm,info in [('Gama',g,g_s,{}),('Replay-Exact128',rep,grid_s+replay_s,{}),('RA-global-Exact128',glob,global_s+summary_s,gi),('RA6-Exact128',ra,ra_s+summary_s,ri),('BF+Exact128',bf,bf_s,{}),('PlainBF',bfcands[0],bfcands[0]['individual_build_s'],{'included_in_bf_grid':True}),('ZGate-Exact128',gate,summary_s+ra_s+bf_s+gate_s,dict(ra_learning_fp=ra_lfp,bf_learning_fp=bf_lfp,winner='BF' if gate is bf else 'RA6'))]:
                exact_row(method,c,kib,tm,info)
        t=time.perf_counter();indexed,ii=R6.select6(s,scores,lm,kib,len(tail));idx_s=time.perf_counter()-t
        idx_fp,_=W.evaluate(indexed,tail,s,safe)
        reference=next(r for r in old['rows'] if r['method']=='RA-PLBF-GT19' and r['budget_kib']==kib)
        assert (idx_fp['fp'],indexed['trees'],indexed['frac'],W.ah(indexed['structure'].fp_static))==(reference['fp'],reference['trees'],reference['cache_frac'],reference['static_flags_sha256'])
        req=index_bytes if indexed['cache_bytes'] else 0
        idxledger=ledger(indexed,req)
        out['rows'].append(dict(method='RA6-prefix',format='prefix',base_budget_kib=kib,auxiliary_ceiling_bytes=kib*1024+index_bytes,trees=indexed['trees'],cache_frac=indexed['frac'],fp=idx_fp['fp'],selection_s=idx_s+summary_s,regression_round37=True,**idxledger))
        t=time.perf_counter();icands=[B.build(s,kib,f,K) for f in E5.FRACS];ibf,_=E5.replay_best(icands,learn,s,safe);ibf_s=time.perf_counter()-t
        ibf_fp,_=W.evaluate(ibf,tail,s,safe);refbf=next(r for r in old['rows'] if r['method']=='BF+Cache' and r['budget_kib']==kib)
        assert ibf_fp['fp']==refbf['fp'] and ibf['frac']==refbf['cache_frac']
        out['rows'].append(dict(method='BF+prefix',format='prefix',base_budget_kib=kib,auxiliary_ceiling_bytes=kib*1024+index_bytes,trees=0,cache_frac=ibf['frac'],fp=ibf_fp['fp'],selection_s=ibf_s,regression_round37=True,**ledger(ibf,index_bytes if ibf['cache_bytes'] else 0)))
        total=kib*1024+index_bytes
        t=time.perf_counter();large=[bf_build(s,total,f,sys.modules['exact41']) for f in E5.FRACS];large_best,_=replay_best(large,learn,s,qblob,qoffsets);large_s=time.perf_counter()-t
        exact_row('PlainBF-envelope',large[0],kib,large[0]['individual_build_s'],{'included_in_bf_grid':True},total)
        exact_row('BF+Exact128-envelope',large_best,kib,large_s,ceiling=total)
        actual=idxledger['auxiliary_total_bytes'];t=time.perf_counter();actual_bf=bf_build(s,actual,0.,K);actual_s=time.perf_counter()-t
        exact_row('PlainBF-RAactual',actual_bf,kib,actual_s,ceiling=actual)
        t=time.perf_counter();positions=np.searchsorted(member_index,s.h1q);match=(positions<len(member_index))&(member_index[np.minimum(positions,len(member_index)-1)]==s.h1q)
        fp=int(match[tail].sum());direct_s=time.perf_counter()-t
        out['rows'].append(dict(method='DirectHashIndex',format='hash_positive_verified_by_backend',base_budget_kib=kib,auxiliary_ceiling_bytes=total,fp=fp,filter_bytes=index_bytes,required_extra_index_bytes=0,auxiliary_total_bytes=index_bytes,selection_s=0.,negative_replay_s=direct_s,strict_static_zero_fn=True))
        W.save(outpath,out)
    assert len(out['rows'])==39 and E5.K is K
    check();out.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    W.save(outpath,out);print('COMPLETE',seed,len(out['rows']),out['wall_s'],flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('seed',type=int,choices=SEEDS);a=p.parse_args()
    try:run(a.seed)
    except Exception as e:W.save(ROOT/f'results/seed{a.seed}.failure.json',dict(status='failed',error=repr(e)));raise

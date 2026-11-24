import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data44 import *
from worker41 import bf_build,ledger
METHODS=('Gama','Replay','RA-global','RA6-Exact128','BF+Exact128','PlainBF','ZGate-Exact128')


def run(cluster,seed):
    frozen=check();start=time.perf_counter();outpath=ROOT/f'results/{cluster}_{seed}.json';assert not outpath.exists()
    qualification=json.loads((ROOT/f'results/{cluster}_qualification.json').read_text());assert qualification['eligible_for_method_comparison'];ref=next(r for r in qualification['diagnostics'] if r['seed']==seed)
    path=ROOT/f'cache/{cluster}.npz';meta=json.loads((ROOT/f'results/{cluster}_data.json').read_text());assert sha(path)==meta['prepared_sha256']
    t=time.perf_counter();s,X,learn,tail=prepare(path,seed);sp=s.split
    with np.load(path,allow_pickle=False) as d:blob,offsets,trace,ce,le=[d[k] for k in ('blob','offsets','trace','catalog_end','learn_end')]
    ce,le=int(ce),int(le);keys=[blob[offsets[i]:offsets[i+1]].tobytes() for i in range(len(s.ids))]
    qblob,qoff=pack([keys[i] for i in np.flatnonzero(sp['neg_test'])]);lengths=np.diff(offsets);del keys
    hashes=E5.C.splitmix64(s.ids^np.uint64(E5.C.H1_SALT)^np.uint64(seed));mixed=trace[le:];mixed=mixed[(s.y|sp['neg_test'])[mixed]]
    prepared_s=time.perf_counter()-t
    assert W.ah(learn)==ref['learning_sha256'] and W.ah(tail)==ref['tail_sha256']
    t=time.perf_counter();use=sp['member_train']|sp['neg_train']
    model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[use],label=s.y[use]),num_boost_round=200)
    training_s=time.perf_counter()-t;assert model.num_trees()==200,'Model stopped early; retain failure'
    t=time.perf_counter();scores=W.prefix_raw_scores(model,X,E5.TREES)
    for trees in E5.TREES:E5.R._MODEL_ARRAYS[s.name,trees]=W.model_arrays(model,trees)
    held=(s.y&~sp['member_train'])|sp['neg_val'];assert np.isclose(W.auc(s.y[held],scores[16][held]),ref['development_auc16'],rtol=0,atol=1e-12)
    score_s=time.perf_counter()-t
    t=time.perf_counter()
    for trees in E5.TREES:E5.tree(s,scores,trees)
    tree_s=time.perf_counter()-t
    t=time.perf_counter();lm=W.summarize19(learn);summary_s=time.perf_counter()-t
    t=time.perf_counter();warm=bf_build(s,4096,.1,E);E.evaluate(warm,learn[:2],s,qblob,qoff);E5.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.);jit_s=time.perf_counter()-t
    length_support=np.unique(lengths[s.y]);cheap_rejects=int((~np.isin(lengths[sp['neg_test']][tail],length_support)).sum())
    out=dict(status='running',cluster=cluster,seed=seed,freeze_sha256=frozen,prepared_sha256=sha(path),members=len(s.h1m),query_negative_keys=len(s.h1q),learning_queries=len(learn),tail_negative_queries=len(tail),tail_mixed_queries=len(mixed),tail_mixed_members=int(s.y[mixed].sum()),learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),mixed_sha256=W.ah(mixed),input_prepare_s=prepared_s,model_training_s=training_s,score_prepare_s=score_s,shared_tree_prepare_s=tree_s,summary_s=summary_s,JIT_s=jit_s,feature_payload_bytes=X.nbytes,raw_key_payload_bytes=blob.nbytes,required_extra_member_index_bytes=0,task=meta['task'],original_backend_NotFound_inferred=False,cheap_length_support=dict(negative_rejects=cheap_rejects,negative_calls=len(tail)-cheap_rejects,member_FN=0,support_array_bytes=sys.getsizeof(length_support),scope='supports only, not a complete filter or semantic namespace oracle'),rows=[])
    for kib in budgets(len(s.h1m)):
        with E.exact_layout():
            t=time.perf_counter();g=E5.gama(E5.candidates(s,scores,kib,fracs=(0.,)));gs=time.perf_counter()-t
            t=time.perf_counter();cands=E5.candidates(s,scores,kib);grid_s=time.perf_counter()-t
            t=time.perf_counter();rep,_=E.replay_best(cands,learn,s,qblob,qoff);replay_s=time.perf_counter()-t
            t=time.perf_counter();glob,gi=RA.select(s,scores,lm,kib,len(tail),RA.Config(mode='global',new_mix=0.));glob_s=time.perf_counter()-t
            t=time.perf_counter();ra,ri=R6.select6(s,scores,lm,kib,len(tail));ra_s=time.perf_counter()-t
            t=time.perf_counter();bc=[bf_build(s,kib*1024,f,E) for f in E5.FRACS];bf,bfp=E.replay_best(bc,learn,s,qblob,qoff);bf_s=time.perf_counter()-t
            t=time.perf_counter();rfp,_,_=E.evaluate(ra,learn,s,qblob,qoff);gate=bf if bfp<=rfp else ra;gate_s=time.perf_counter()-t
        choices=[('Gama',g,gs,{}),('Replay',rep,grid_s+replay_s,dict(grid_s=grid_s,learning_replay_s=replay_s)),('RA-global',glob,glob_s+summary_s,gi),('RA6-Exact128',ra,ra_s+summary_s,ri),('BF+Exact128',bf,bf_s,{}),('PlainBF',bc[0],bc[0]['individual_build_s'],{}),('ZGate-Exact128',gate,summary_s+ra_s+bf_s+gate_s,dict(winner='BF' if gate is bf else 'RA6',RA_learning_fp=rfp,BF_learning_fp=bfp))]
        for method,c,select_s,info in choices:
            t=time.perf_counter();fp,data,cnt=E.evaluate(c,tail,s,qblob,qoff);replay_s=time.perf_counter()-t
            spec=E.layout(c['cache_bytes']);before=W.ah(data);hits=int(E.member_hits(data,hashes,blob,offsets,np.flatnonzero(s.y),spec['buckets']));assert hits==0 and before==W.ah(data)
            flags=np.ones(len(s.ids),np.bool_);flags[sp['neg_test']]=c['structure'].fp_static;state=E.allocate(spec)
            t=time.perf_counter();mc=E.replay(mixed,hashes,blob,offsets,flags,s.y,state,spec['buckets']);mixed_s=time.perf_counter()-t
            assert mc[4]==0 and mc[2]==out['tail_mixed_members'] and mc[1]==fp and np.array_equal(state,data)
            row=dict(method=method,budget_kib=kib,trees=c['trees'],cache_frac=c['frac'],fp=fp,mixed_backend_calls=int(mc[0]),member_fn=0,final_member_cache_hits=hits,selection_s=select_s,negative_replay_s=replay_s,mixed_replay_s=mixed_s,cache_sha256=before,flags_sha256=W.ah(c['structure'].fp_static),selection_info=info,**ledger(c))
            out['rows'].append(row);save(outpath,out);print('RESULT',cluster,seed,kib,method,'FP',fp,'trees',c['trees'],flush=True)
    assert len(out['rows'])==len(budgets(len(s.h1m)))*7;check()
    out.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);save(outpath,out);print('COMPLETE',cluster,seed,flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('cluster',choices=CLUSTERS);p.add_argument('seed',type=int,choices=SEEDS);a=p.parse_args()
    try:run(a.cluster,a.seed)
    except Exception as e:save(ROOT/f'results/{a.cluster}_{a.seed}.failure.json',dict(status='failed',error=repr(e)));raise

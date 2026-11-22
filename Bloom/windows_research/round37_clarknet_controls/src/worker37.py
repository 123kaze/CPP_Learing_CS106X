"""Five unchanged selectors plus separately labeled fixed-region controls on ClarkNet."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from control37 import ROOT,WR,BLOOM,W,E5,RA,M,SEEDS,budgets,check_freeze,controls,np
import json
import resource
import time
INPUT=WR/'round36_http_qualification/cache/clarknet.npz'


def run(seed):
    start=time.perf_counter();frozen=check_freeze();output=ROOT/f'results/seed{seed}.json'
    assert not output.exists(), 'Refuse result overwrite'
    qualification=json.loads((WR/'round36_http_qualification/results/clarknet.json').read_text())
    assert qualification['qualification']['eligible_for_full_comparison']
    qref=next(r for r in qualification['diagnostics'] if r['seed']==seed)
    t=time.perf_counter();s,X,learn,tail=W.prepare(INPUT,seed);data_s=time.perf_counter()-t
    assert len(learn)==qref['learning_requests'] and len(tail)==qref['tail_requests']
    assert len(s.h1m)==32581 and budgets(len(s.h1m))==(8,16,32)
    assert W.get_num_threads()==1
    sp=s.split;train=sp['member_train']|sp['neg_train'];H=len(tail)
    t=time.perf_counter()
    model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,
                          deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[train],label=s.y[train]),num_boost_round=200)
    train_s=time.perf_counter()-t;assert model.num_trees()==200
    t=time.perf_counter();scores=W.prefix_raw_scores(model,X,E5.TREES)
    for trees in E5.TREES:
        E5.R._MODEL_ARRAYS[s.name,trees]=W.model_arrays(model,trees)
        assert np.array_equal(scores[trees],model.predict(X,raw_score=True,num_iteration=trees,num_threads=1))
    score_s=time.perf_counter()-t;s.q_score=scores[200][sp['neg_test']]
    held=(s.y&~sp['member_train'])|sp['neg_val']
    auc16=W.auc(s.y[held],scores[16][held])
    assert np.isclose(auc16,qref['development_auc'],atol=1e-12,rtol=0)
    t=time.perf_counter();member_index=np.sort(s.h1m);safe=E5.E.CC.safe_prefix_lengths(member_index,s.h1q);index_s=time.perf_counter()-t
    t=time.perf_counter();lm=W.summarize19(learn);summary_s=time.perf_counter()-t
    t=time.perf_counter();warm=W.B.build(s,4,.1,E5.K);W.evaluate(warm,learn[:2],s,safe)
    E5.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.)
    M.physical(np.array([len(s.h1m)],float),np.array([.5]),s.h1m,s.h1q,np.zeros(len(s.h1m),np.int32),np.zeros(len(s.h1q),np.int32),len(s.h1m)*8)
    jit_s=time.perf_counter()-t
    out=dict(status='running',dataset='clarknet',seed=seed,freeze_sha256=frozen,input_sha256=W.sha(INPUT),
             members=len(s.h1m),negative_pool=len(s.h1q),learning_queries=len(learn),tail_queries=H,
             learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),development_auc16=auc16,
             data_preparation_s=data_s,model_training_s=train_s,score_preparation_and_verification_s=score_s,
             index_preparation_s=index_s,learning_summary_s=summary_s,jit_warm_s=jit_s,
             backend_index_payload_bytes=member_index.nbytes,backend_index_physical_bytes=sys.getsizeof(member_index),
             feature_matrix_bytes=X.nbytes,score_arrays_bytes=sum(a.nbytes for a in scores.values()),
             native_threads=1,rows=[],controls=[])
    for kib in budgets(len(s.h1m)):
        t=time.perf_counter();g=E5.gama(E5.candidates(s,scores,kib,fracs=(0.,)));g_s=time.perf_counter()-t
        t=time.perf_counter();cands=E5.candidates(s,scores,kib);grid_s=time.perf_counter()-t
        t=time.perf_counter();replay,_=E5.replay_best(cands,learn,s,safe);replay_s=time.perf_counter()-t
        t=time.perf_counter();glob,gi=RA.select(s,scores,lm,kib,H,RA.Config(mode='global',new_mix=0.));glob_s=time.perf_counter()-t
        t=time.perf_counter();ra,ri=W.ra6.select6(s,scores,lm,kib,H);ra_s=time.perf_counter()-t
        t=time.perf_counter();bf_cands=[W.B.build(s,kib,f,E5.K) for f in E5.FRACS];bf_grid_s=time.perf_counter()-t
        t=time.perf_counter();bf,_=E5.replay_best(bf_cands,learn,s,safe);bf_replay_s=time.perf_counter()-t
        choices=[('Gama',g,g_s,{}),('Replay',replay,grid_s+replay_s,dict(grid_build_s=grid_s,learning_replay_s=replay_s,candidates=len(cands))),
                 ('RA-global',glob,summary_s+glob_s,gi),('RA-PLBF-GT19',ra,summary_s+ra_s,ri),
                 ('BF+Cache',bf,bf_grid_s+bf_replay_s,dict(grid_build_s=bf_grid_s,learning_replay_s=bf_replay_s,candidates=len(bf_cands)))]
        for method,c,select_s,info in choices:
            t=time.perf_counter();result,member_fn=W.evaluate(c,tail,s,safe);evaluation_s=time.perf_counter()-t;st=c['structure']
            assert st.used_bytes==st.model_bytes+st.metadata_bytes+st.array_overhead_bytes+st.filter_bytes+c['cache_bytes']<=kib*1024
            out['rows'].append(dict(method=method,budget_kib=kib,trees=c['trees'],cache_frac=c['frac'],**result,member_fn=member_fn,
                                   total_bytes=int(st.used_bytes),model_payload_bytes=int(st.model_bytes),bf_payload_bytes=int(st.filter_bytes),
                                   metadata_bytes=int(st.metadata_bytes),array_header_bytes=int(st.array_overhead_bytes),cache_physical_bytes=c['cache_bytes'],
                                   backend_index_physical_bytes=sys.getsizeof(member_index),build_and_select_s=select_s,tail_replay_s=evaluation_s,
                                   selection_info=info,static_flags_sha256=W.ah(st.fp_static),
                                   regions=W.region_diagnostics(s,scores,c['trees'],c,learn,tail) if c['trees'] else None))
            W.save(output,out)
            print('MAIN',seed,kib,method,'FP',result['fp'],'trees',c['trees'],'frac',c['frac'],flush=True)
        controlled=controls(s,scores,lm,H,kib,tail,safe);out['controls'].append(controlled);W.save(output,out)
        print('CONTROL',seed,kib,controlled['status'],[(r['arm'],r['fp']) for r in controlled['rows']],flush=True)
    assert len(out['rows'])==15 and len(out['controls'])==3
    check_freeze();out.update(status='complete',wall_s=time.perf_counter()-start,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
    W.save(output,out);print('COMPLETE_SEED',seed,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('seed',type=int,choices=SEEDS);a=p.parse_args()
    try:run(a.seed)
    except Exception as e:
        W.save(ROOT/f'results/seed{a.seed}.failure.json',dict(status='failed',error=repr(e)))
        raise

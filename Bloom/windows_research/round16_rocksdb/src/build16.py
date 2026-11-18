"""Three fresh training/selection repetitions; serialize only deployed numeric arrays."""
from common16 import *
import argparse
import time
from types import SimpleNamespace
import numpy as np
import lightgbm as lgb
import rocksdict as Rocks
from native16 import *
sys.path.insert(0,str(WR/'round13_complete/src'))
from leaf_scores import prefix_raw_scores
from end_to_end import model_arrays
sys.path.insert(0,str(WR/'round7_original_e2e/src'))
from ra6_worker import warm_jit


def main(rep,tag):
    dest=ROOT/'inputs'/tag;dest.mkdir(exist_ok=True)
    done=ROOT/f'results/{tag}_rep{rep}.json'
    assert not done.exists(),'Completed or failed construction exists'
    assert not any(dest.glob(f'*_rep{rep}_*.npz')),'Partial artifacts exist; no automatic retry'
    warm_jit()
    ids,y,X,features=C.load_dataset(DS);sp=C.make_split(ids,y,DS)
    request=np.load(ROOT/'inputs/requests.npz');ri=request['ids'];rx=request['X'];nm=int(request['members'])
    assert np.array_equal(ri,np.concatenate([ids[y],ids[sp['neg_test']]]))
    h=C.splitmix64(ids^np.uint64(C.H1_SALT))
    setup=SimpleNamespace(name=DS,ids=ids,y=y,split=sp,h1m=h[y],h1q=h[sp['neg_test']],q_ids=ids[sp['neg_test']])
    start=time.perf_counter();train=sp['member_train']|sp['neg_train']
    model=lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=1,
                         deterministic=True,force_col_wise=True,verbose=-1),lgb.Dataset(X[train],label=y[train],feature_name=features),num_boost_round=200)
    train_s=time.perf_counter()-start
    start=time.perf_counter();scores=prefix_raw_scores(model,X,E5.TREES)
    for t in E5.TREES:E5.R._MODEL_ARRAYS[DS,t]=model_arrays(model,t)
    setup.q_score=scores[48][sp['neg_test']]
    for t in E5.TREES:E5.tree(setup,scores,t)
    scoring_s=time.perf_counter()-start
    # Construction-only statistics for replay and safety; never used to accept a live query.
    start=time.perf_counter();sorted_m=np.sort(setup.h1m)
    safe=E5.E.CC.safe_prefix_lengths(sorted_m,setup.h1q)
    cache_prepare_s=time.perf_counter()-start
    assert not np.intersect1d(setup.h1m,setup.h1q).size
    # Warm BF/replay specializations on unrelated tiny inputs before readiness timers.
    tiny=BF.allocate(2,1024,0);BF.insert_all(tiny,setup.h1m[:2]);BF.query_all(tiny,setup.h1q[:2])
    K.simulate(np.array([0,1],np.int64),setup.h1q[:2],safe[:2],np.array([True,False]),1024)
    opts,blockcache=db_options(CACHES['fit'])
    db=Rocks.Rdict(str(ROOT/'db/url'),opts,access_type=Rocks.AccessType.read_only())
    result=dict(status='running',rep=rep,tag=tag,train_s=train_s,score_prepare_s=scoring_s,
                offline_cache_prepare_s=cache_prepare_s,model_sha256=__import__('hashlib').sha256(model.model_to_string().encode()).hexdigest(),methods={})
    for workload in WORKLOADS:
        learn=np.load(ROOT/f'inputs/{workload}_learn.npy');tail=np.load(ROOT/f'inputs/{workload}_tail.npy')
        assert len(learn)==LEARN
        keys=[key_bytes(setup.q_ids[i]) for i in learn]
        start=time.perf_counter()
        missing=[db.get(k) is None for k in keys]  # actual authoritative feedback acquisition
        acquisition=time.perf_counter()-start
        assert all(missing)
        for method in METHODS[1:]:
            begin=time.perf_counter()
            if method=='BFCache':
                cands=[BF.build(setup,KIB,f,K) for f in E5.FRACS]
                c,info=E5.replay_best(cands,learn,setup,safe)
            elif method=='Gama':
                cands=E5.candidates(setup,scores,KIB,fracs=(0.,))
                c=E5.gama(cands)
            elif method=='Replay':
                cands=E5.candidates(setup,scores,KIB)
                c,info=E5.replay_best(cands,learn,setup,safe)
            else:
                lm=J.RA.ra4.summarize(learn,True)
                c,info=J.ra6.select6(setup,scores,lm,KIB,TAIL)
            a=arrays_for(setup,scores,c,method=='BFCache')
            select_s=time.perf_counter()-begin
            logical=c['structure'].used_bytes
            measured_keys=('bf',) if method=='BFCache' else tuple(k for k in KEYS if k not in ('bf','sorted_m'))
            actual_arrays=sum(sys.getsizeof(a[k]) for k in measured_keys)+c['cache_bytes']
            assert actual_arrays<=KIB*1024,(method,actual_arrays)
            native=make_native(a,method=='BFCache',c['cache_bytes'])
            flags=probe_all(native,ri,rx)
            assert (flags[:nm]==1).all() and np.array_equal(flags[nm:]==1,c['structure'].fp_static)
            # Oracle reference is used for correctness only, outside all database measurement.
            native=make_native(a,method=='BFCache',c['cache_bytes'])
            reference_fp=reference_stream(native,tail,ri,rx,nm)
            assert (probe_all(native,ri[:nm],rx[:nm])==1).all()
            meta=dict(method=method,workload=workload,rep=rep,trees=c['trees'],frac=c['frac'],
                      cache_bytes=c['cache_bytes'],frozen_charged_bytes=logical,actual_deployment_array_bytes=actual_arrays,
                      external_member_index_bytes=a['sorted_m'].nbytes,selection_build_s=select_s,
                      train_s=0. if method=='BFCache' else train_s,score_prepare_s=0. if method=='BFCache' else scoring_s,
                      learning_db_acquire_s=0. if method=='Gama' else acquisition,
                      offline_cache_prepare_s=0. if method=='Gama' else cache_prepare_s,
                      expected_db_negative_misses=int(reference_fp),fixed_member_checks_passed=True,
                      full_pool_flags_sha256=ah(c['structure'].fp_static),model_sha256=result['model_sha256'])
            meta['train_to_ready_s']=sum(meta[k] for k in ('selection_build_s','train_s','score_prepare_s','learning_db_acquire_s','offline_cache_prepare_s'))
            artifact=dest/f'{workload}_rep{rep}_{method}.npz'
            np.savez(artifact,**a)
            meta['artifact_sha256']=digest(artifact)
            save(artifact.with_suffix('.json'),meta)
            result['methods'][f'{workload}/{method}']=meta
            print(f'BUILT {tag} rep{rep} {workload} {method}: FP={reference_fp} ready={meta["train_to_ready_s"]:.3f}s arrays={actual_arrays}',flush=True)
    db.close();result['status']='complete';save(done,result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rep',type=int,required=True);p.add_argument('--tag',default='filters');a=p.parse_args();main(a.rep,a.tag)

"""LightGBM unchanged; only negative training weights differ between arms."""
from weights26 import *
from types import SimpleNamespace
import argparse
import json
import time
import hashlib
import ctypes
from statistics import median
import lightgbm as lgb
from numba import get_num_threads
sys.path.insert(0,str(WR/'round13_complete/src'));from leaf_scores import prefix_raw_scores
sys.path.insert(0,str(WR/'round6_bucket/src'));import e789 as J
sys.path.insert(0,str(WR/'round23_lightweight/src'));import models23 as M
from end_to_end import model_arrays
ROOT=Path(__file__).resolve().parents[1]
SETTINGS={'url':128,'caida':256,'caida_tcp_flow':32}
PREFIXES=(1,4,8,16,48,160)
ARMS=('Uniform','TrafficGT','EscapeGT')
CACHE_FRACS=(0.,.1)


def ah(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()

def save(path,obj):
    p=path.with_suffix('.json.tmp');p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');p.replace(path)


def train_model(X,y,weight,rounds):
    # Exactly identical parameters and training examples across arms.
    return lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=1,
          deterministic=True,force_col_wise=True,verbose=-1),
          lgb.Dataset(X,label=y,weight=weight),num_boost_round=rounds)


def set_model(setup,model,t):
    E5.R._MODEL_ARRAYS[setup.name,t]=model_arrays(model,t)
    E5._TREE.pop((setup.name,t),None)
    E5.R._GSETUPS.clear()


def run(ds,output):
    if ds.endswith('_tcp_flow'):
        sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
    C=E5.C;kib=SETTINGS[ds]
    lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));f=lib.openblas_get_num_threads;f.restype=ctypes.c_int
    assert f()==get_num_threads()==1
    folder=C.CACHE/ds
    for n in ('data.npz','scores.npz'):assert (folder/n).exists(),'Prepared data required'
    ids,y,X,features=C.load_dataset(ds);split=C.make_split(ids,y,ds)
    h=C.splitmix64(ids^np.uint64(C.H1_SALT));train=split['member_train']|split['neg_train']
    with np.load(folder/'scores.npz') as qdata:original_q=qdata['score'][split['neg_test']]
    setup=SimpleNamespace(name=ds,ids=ids,y=y,split=split,h1m=h[y],h1q=h[split['neg_test']],q_ids=ids[split['neg_test']],q_score=original_q)
    learnstream=E5.base_stream(setup,'真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部',None if ds.endswith('_flow') else ('zipf',None,1.),0)
    learn=learnstream[:len(learnstream)//4];H=len(learnstream)-len(learn)
    safe=E5.E.CC.safe_prefix_lengths(np.sort(setup.h1m),setup.h1q)
    # Training arrays are fixed and disjoint from learning keys at key identity level.
    Xtr=X[train];ytr=y[train];negative_positions=~ytr
    assert not np.intersect1d(ids[split['neg_train']],setup.q_ids[np.unique(learn)]).size
    t=time.perf_counter();ref_model=train_model(Xtr,ytr,None,16);reference_train_s=time.perf_counter()-t
    t=time.perf_counter();ref_score=ref_model.predict(X,raw_score=True,num_threads=1)
    set_model(setup,ref_model,16)
    reference=E5.build(setup,{16:ref_score},16,kib,.1)
    assert reference is not None
    weights,diagnostic=estimate(ref_score,y,split,reference,E5.tree(setup,{16:ref_score},16),learn,H)
    reference_prepare_s=time.perf_counter()-t
    space=J.space_of(setup,ds)
    rng=np.random.default_rng(2602)
    requests=np.concatenate([rng.integers(space.nm,space.nm+space.nq,90000,dtype=np.int64),rng.integers(0,space.nm,10000,dtype=np.int64)])
    rng.shuffle(requests)
    out=dict(status='running',dataset=ds,budget_kib=kib,seed=1,workload_seed=0,
       workload='真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部',learning_queries=len(learn),tail_queries=H,
       input_features=features,train_rows=int(train.sum()),members=int(y.sum()),test_pool=len(setup.h1q),
       stream_sha256=ah(learnstream),train_ids_sha256=ah(ids[train]),training_negative_weight_map=diagnostic,
       reference_tree_count=16,reference_cache_fraction=.1,reference_train_s=reference_train_s,reference_prepare_s=reference_prepare_s,
       reference_model_bytes=reference['structure'].model_bytes,
       openblas_threads=1,numba_threads=1,arms={},results=[])
    for arm in ARMS:
        sample_weight=np.ones(len(ytr));sample_weight[negative_positions]=weights[arm]
        assert (sample_weight[ytr]==1).all() and np.isclose(sample_weight[negative_positions].mean(),1.)
        t=time.perf_counter();model=train_model(Xtr,ytr,None if arm=='Uniform' else sample_weight,160);training_s=time.perf_counter()-t
        t=time.perf_counter();scores=prefix_raw_scores(model,X,PREFIXES);scoring_s=time.perf_counter()-t
        if arm=='Uniform':assert np.array_equal(scores[16],ref_score),'Reference16 is not the same unweighted prefix'
        out['arms'][arm]=dict(train_s=training_s,score_prepare_s=scoring_s,weight_sha256=ah(sample_weight),
           negative_weight_min=float(sample_weight[negative_positions].min()),negative_weight_max=float(sample_weight[negative_positions].max()),
           extra_weight_acquisition_s=0. if arm=='Uniform' else reference_train_s+reference_prepare_s,
           note='Single fixed-model seed. Weighted paths pay for their fixed reference model and proxy transfer; cached scores are not free model training.')
        print(f'TRAINED {ds} {arm}: {training_s:.3f}s',flush=True)
        for tcount in PREFIXES:
            set_model(setup,model,tcount)
            model_args=model_arrays(model,tcount)
            meta=dict(code=5,features=X.shape[1]);args=M.arguments(meta,model_args)
            sample=np.linspace(0,len(X)-1,10000,dtype=np.int64)
            M.native_scores(X[:2],*args)
            assert np.allclose(M.native_scores(X[sample],*args),scores[tcount][sample],rtol=1e-8,atol=1e-8)
            checksum=M.score_checksum(space.X,requests,*args);score_times=[]
            for _ in range(3):
                begin=time.perf_counter_ns();val=M.score_checksum(space.X,requests,*args);score_times.append((time.perf_counter_ns()-begin)/len(requests));assert val==checksum
            for frac in CACHE_FRACS:
                begin=time.perf_counter();c=E5.build(setup,scores,tcount,kib,frac)
                if c is None:
                    out['results'].append(dict(arm=arm,trees=tcount,frac=frac,status='infeasible',reason='Model plus cache exceeds budget'));continue
                build_s=time.perf_counter()-begin
                exe=J.Exe(setup,scores,c,space)
                nm=space.nm
                count,accepted=exe.run(np.arange(nm,dtype=np.int64),0,nm,1,exe.fresh_cache());assert count[2]==0 and accepted.all()
                pool_idx=np.arange(space.nq,dtype=np.int64)+nm
                count,accepted=exe.run(pool_idx,0,len(pool_idx),1,exe.fresh_cache())
                assert np.array_equal(accepted.astype(bool),c['structure'].fp_static)
                # Native correctness with a populated cache, separate from timing.
                exe.run(requests,0,len(requests),2,exe.fresh_cache())
                times=[];reference_counts=None
                for _ in range(3):
                    cache=exe.fresh_cache();begin=time.perf_counter_ns()
                    counts,acc=exe.run(requests,0,len(requests),2,cache)
                    times.append((time.perf_counter_ns()-begin)/len(requests))
                    assert counts[2]==0
                    if reference_counts is None:reference_counts=counts.copy()
                    else:assert np.array_equal(reference_counts,counts)
                    assert E5.K.count_member_hits(cache,setup.h1m,exe.spec['buckets'],40,exe.spec['Q'],exe.spec['ob'],exe.spec['slot_bits'],4)==0 if c['cache_bytes'] else True
                # Only after weight fitting/training evaluate the original held-out query tail.
                result=E5.evaluate(c,learnstream[len(learn):],setup,safe)
                st=c['structure'];reg=E5.D.region_of_segment(st.b)
                # Proxy-only final-region KL using predicted reference residual mass is not meaningful
                # across new scorers; instead report class separation on validation, no oracle tail KL gate.
                td=E5.tree(setup,scores,tcount)
                p=np.bincount(reg,weights=td.g,minlength=5);p=p/p.sum()
                q=np.bincount(reg,weights=td.v+1.,minlength=5);q=q/q.sum()
                kl=float(np.sum(p[p>0]*np.log(p[p>0]/q[p>0])))
                row=dict(arm=arm,trees=tcount,frac=frac,status='ok',cache_bytes=c['cache_bytes'],total_bytes=st.used_bytes,
                   model_bytes=st.model_bytes,bf_bytes=st.filter_bytes,model_array_bytes_with_headers=sum(sys.getsizeof(v) for v in model_args.values()),
                   tail_fp=int(result['fp']),tail_fpr=result['fp']/H,static_pool_fp=int(st.fp_static.sum()),static_flags_sha256=ah(st.fp_static),
                   native_model_ns_all=score_times,native_model_ns_median=median(score_times),native_full_ns_all=times,native_full_ns_median=median(times),
                   filter_build_s=build_s,member_fn=0,native_pool_flags_equal=True,validation_region_KL=kl)
                out['results'].append(row);save(output,out)
                print(f'FILTER {ds} {arm} t={tcount} cache={frac}: tailFP={row["tail_fp"]} score={median(score_times):.1f}ns',flush=True)
        del scores,model
    assert len(out['results'])==len(ARMS)*len(PREFIXES)*len(CACHE_FRACS)
    out['status']='complete';save(output,out)
    print(f'COMPLETE {ds}: {len(out["results"])} configurations',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=SETTINGS,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(),'Refuse overwrite'
    run(a.dataset,a.output)

"""Round8 RA6 worker copied into round13 with loop/leaf scoring and equivalence digests.

Training, native construction and query measurements stay as in the original worker.
Score/model hashing happens after common_train_prepare_s and outside selection timers.
"""
import argparse
import hashlib
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'round8_paper_data/src'))
import paper_common as P
import numpy as np
import lightgbm as lgb
from leaf_scores import prefix_raw_scores
sys.path.insert(0,str(P.ROOT.parent/'round6_bucket/src'))
import e789 as J
from end_to_end import model_arrays
from ra6_worker import warm_jit
E5,R,C=J.E5,J.R,J.C


def digest_array(a):
    return hashlib.sha256(a.view(np.uint8)).hexdigest()


def main(a):
    out=dict(method='RA6',dataset=a.dataset,budget_kib=a.budget,status='running',scoring=a.scoring,
             chunk_rows=a.chunk_rows,source_sha256=P.S.digest(P.ROOT.parent/'round6_bucket/src/ra6.py'),
             worker_sha256=P.S.digest(Path(__file__)),leaf_helper_sha256=P.S.digest(HERE/'leaf_scores.py'),
             lightgbm=lgb.__version__)
    try:
        out['jit_setup_s']=warm_jit()
        t=time.perf_counter()
        ids,y,X,features,sp=P.data(a.dataset)
        out['read_prepare_s']=time.perf_counter()-t
        begin=time.perf_counter()
        train=sp['member_train']|sp['neg_train']
        booster=lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,verbose=-1,
                               num_threads=1,seed=1,deterministic=True,force_col_wise=True),
                          lgb.Dataset(X[train],label=y[train],feature_name=features),num_boost_round=200)
        out['train_s']=time.perf_counter()-begin
        t=time.perf_counter()
        h=C.splitmix64(ids ^ np.uint64(C.H1_SALT))
        setup=SimpleNamespace(name=a.dataset,ids=ids,y=y,split=sp,h1m=h[y],h1q=h[sp['neg_test']],q_ids=ids[sp['neg_test']])
        needed=y|sp['neg_val']|sp['neg_test']
        score_X=X[needed]
        scores={}
        if a.scoring=='loop':
            for trees in E5.TREES:
                R._MODEL_ARRAYS[a.dataset,trees]=model_arrays(booster,trees)
                score=np.zeros(len(ids))
                score[needed]=booster.predict(score_X,raw_score=True,num_iteration=trees,num_threads=1)
                scores[trees]=score
        else:
            prefixes=prefix_raw_scores(booster,score_X,E5.TREES,a.chunk_rows)
            for trees in E5.TREES:
                R._MODEL_ARRAYS[a.dataset,trees]=model_arrays(booster,trees)
                score=np.zeros(len(ids))
                score[needed]=prefixes.pop(trees)
                scores[trees]=score
            del prefixes
        del score_X
        space=SimpleNamespace(X=np.ascontiguousarray(np.vstack([X[y],X[sp['neg_test']]])),
                              h=np.concatenate([h[y],h[sp['neg_test']]]),
                              member=np.concatenate([np.ones(int(y.sum()),np.bool_),np.zeros(int(sp['neg_test'].sum()),np.bool_)]),
                              sorted_m=np.sort(h[y]),nm=int(y.sum()),nq=int(sp['neg_test'].sum()))
        out['score_and_input_prepare_s']=time.perf_counter()-t
        out['common_train_prepare_s']=time.perf_counter()-begin
        out['member_index_bytes']=space.sorted_m.nbytes
        # Checksums are excluded from the measured construction stages above and below.
        t=time.perf_counter()
        out['model_sha256']=hashlib.sha256(booster.model_to_string().encode()).hexdigest()
        out['score_sha256']={str(trees):digest_array(score) for trees,score in scores.items()}
        out['verification_hash_s']=time.perf_counter()-t
        out['workloads']={}
        for name in ('once','zipf'):
            folder=P.ROOT/'inputs'/a.dataset
            learn,tail=np.load(folder/f'{name}_learn.npy'),np.load(folder/f'{name}_tail.npy')
            t=time.perf_counter()
            lm=J.RA.ra4.summarize(learn,True)
            c,info=J.ra6.select6(setup,scores,lm,a.budget,len(tail))
            exe=J.Exe(setup,scores,c,space)
            construction=time.perf_counter()-t
            assert c['structure'].used_bytes<=a.budget*1024
            idx=np.linspace(0,len(space.X)-1,min(10000,len(space.X)),dtype=np.int64)
            raw=J.scores_numba(space.X,idx,*exe.model)
            expected=booster.predict(space.X[idx],raw_score=True,num_iteration=c['trees'],num_threads=1)
            assert np.max(np.abs(raw-expected))<1e-9
            members=np.arange(space.nm,dtype=np.int64)
            cnt,_=exe.run(members,0,space.nm,1,exe.fresh_cache())
            assert cnt[2]==0 and cnt[0]==space.nm
            qi=np.arange(space.nq,dtype=np.int64)+space.nm
            cnt,flags=exe.run(qi,0,space.nq,1,exe.fresh_cache())
            assert np.array_equal(flags.astype(bool),c['structure'].fp_static),'native query differs from built BF'
            native=lambda stream,lo,hi,state:exe.run(stream,lo,hi,2,state)[0]
            result=P.measure_queries(native,exe.fresh_cache,a.dataset,name)
            result.update(trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes'],
                          used_bytes=c['structure'].used_bytes,select_executable_s=construction,
                          train_to_ready_s=out['common_train_prepare_s']+construction,
                          member_false_negatives=0,selection=info,
                          static_flags_sha256=digest_array(c['structure'].fp_static),
                          bf_payload_sha256=digest_array(exe.bits))
            if name=='once':result['pool']=P.full_pool(native,exe.fresh_cache,a.dataset)
            out['workloads'][name]=result
            print(f"QUERY {a.scoring} {a.dataset} {a.budget} {name}: FP={result['fp']} ready={result['train_to_ready_s']:.3f}s",flush=True)
        out['member_false_negatives']=0
        out['status']='ok'
    except Exception:
        out['status']='error';out['error']=traceback.format_exc();print(out['error'],flush=True)
    P.S.finish(out,a.output)
    if out['status']!='ok':raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('dataset',choices=('paper_url','paper_cod'))
    p.add_argument('budget',type=int)
    p.add_argument('output',type=Path)
    p.add_argument('--scoring',choices=('loop','leaf'),required=True)
    p.add_argument('--chunk-rows',type=int,default=32768)
    a=p.parse_args()
    if a.output.exists():p.error('Output exists; refusing overwrite')
    if a.chunk_rows<1:p.error('chunk rows must be positive')
    main(a)

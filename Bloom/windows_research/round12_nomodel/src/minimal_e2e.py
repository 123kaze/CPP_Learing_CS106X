"""Small deterministic end-to-end smoke: generated data -> training -> selection -> native queries.

No downloads, precomputed scores, private files or LaTeX. This is NOT publication
performance evidence. It exercises index-based RA6, Gama and BF+cache on one small
synthetic workload; the original frozen implementations are imported unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np
import lightgbm as lgb
from numba import njit
import baseline as B

sys.path.insert(0,str(B.WR/'round6_bucket/src'))
import e789 as J
from end_to_end import model_arrays

C5=B.CACHES['index']


@njit(cache=True)
def bf_native(data, stream, hashes, sorted_members, state, buckets, q, ob, sb, hb):
    counts=np.zeros(3,np.int64)  # FP, cache hit, BF probes (all input queries are negatives)
    m,k=np.int64(data[1]),np.int64(data[2])
    for x in stream:
        h=hashes[x]
        if buckets and C5.lookup(state,h,buckets,40,q,ob,sb,4):
            counts[1]+=1
            continue
        counts[2]+=1
        yes=True
        for j in range(k):
            p=B.C.bf_pos(h,j,m)
            if (data[B.HEAD_WORDS+(p>>6)]>>np.uint64(p&63)) & np.uint64(1)==0:
                yes=False
                break
        if yes:
            counts[0]+=1
            if buckets:
                C5.insert(state,h,J.safe_len(sorted_members,h),buckets,40,q,ob,sb,4,hb)
    return counts


def run():
    started=time.perf_counter()
    rng=np.random.default_rng(121212)
    size=20000
    X=rng.normal(size=(size,4)).astype(np.float32)
    probability=1/(1+np.exp(-(1.8*X[:,0]-X[:,1]+.5*X[:,2]*X[:,3]-1.5)))
    y=rng.random(size)<probability
    ids=np.arange(size,dtype=np.uint64)
    # Independent deterministic key split; no labels/queries used for selection beyond the learning prefix.
    split_value=B.C.splitmix64(ids ^ np.uint64(B.C.SPLIT_SALT)) / float(2**64)
    split=dict(member_train=y&(split_value<.5),neg_train=(~y)&(split_value<.1),
               neg_val=(~y)&(split_value>=.1)&(split_value<.2),neg_test=(~y)&(split_value>=.2))
    train=split['member_train']|split['neg_train']
    t=time.perf_counter()
    model=lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,
                         deterministic=True,force_col_wise=True,seed=1,verbose=-1),
                    lgb.Dataset(X[train],label=y[train]),num_boost_round=200)
    training=time.perf_counter()-t
    h=B.C.splitmix64(ids ^ np.uint64(B.C.H1_SALT))
    setup=SimpleNamespace(name='round12_synthetic_smoke',ids=ids,y=y,split=split,
                          h1m=h[y],h1q=h[split['neg_test']],q_ids=ids[split['neg_test']])
    t=time.perf_counter()
    scores={}
    for trees in B.E5.TREES:
        scores[trees]=model.predict(X,raw_score=True,num_iteration=trees,num_threads=1)
        B.R._MODEL_ARRAYS[setup.name,trees]=model_arrays(model,trees)
    score_prepare=time.perf_counter()-t
    setup.q_score=scores[48][split['neg_test']]
    sorted_m=np.sort(setup.h1m)
    safe=B.E5.E.CC.safe_prefix_lengths(sorted_m,setup.h1q)
    base=B.E5.base_stream(setup,'zipf1.0',('zipf',min(10000,len(setup.h1q)),1.0),0,200000)
    n=len(base)//4
    learn,tail=base[:n],base[n:]
    kib=8
    space=SimpleNamespace(X=np.ascontiguousarray(np.vstack([X[y],X[split['neg_test']]])),
                          h=np.concatenate([setup.h1m,setup.h1q]),
                          member=np.concatenate([np.ones(int(y.sum()),np.bool_),np.zeros(len(setup.h1q),np.bool_)]),
                          sorted_m=sorted_m,nm=int(y.sum()),nq=len(setup.h1q))
    t=time.perf_counter()
    lm=J.RA.ra4.summarize(learn,True)
    ra,info=J.ra6.select6(setup,scores,lm,kib,len(tail))
    ra_select=time.perf_counter()-t
    t=time.perf_counter()
    gama=B.E5.gama(B.E5.candidates(setup,scores,kib,fracs=(0.,)))
    gama_select=time.perf_counter()-t
    outputs=[]
    for name,c,selection in (('RA6',ra,ra_select),('Gama',gama,gama_select)):
        exe=J.Exe(setup,scores,c,space)
        idx=np.arange(space.nm+space.nq,dtype=np.int64)
        got=J.scores_numba(space.X,idx,*exe.model)
        expected=np.concatenate([scores[c['trees']][y],scores[c['trees']][split['neg_test']]])
        assert np.max(np.abs(got-expected))<1e-9
        counts,accepted=exe.run(idx,0,len(idx),1,exe.fresh_cache())
        assert counts[2]==0 and accepted[:space.nm].all()
        assert np.array_equal(accepted[space.nm:].astype(bool),c['structure'].fp_static)
        state=exe.fresh_cache()
        native,_=exe.run(tail+space.nm,0,len(tail),2,state)
        replay=B.E5.evaluate(c,tail,setup,safe)
        assert int(native[1])==replay['fp']
        # Check every member with the populated cache, not merely with an empty one.
        midx=np.arange(space.nm,dtype=np.int64)
        _,accepted_members=exe.run(midx,0,space.nm,2,state)
        assert accepted_members.all()
        outputs.append(dict(method=name,trees=c['trees'],cache_bytes=c['cache_bytes'],
                            total_bytes=c['structure'].used_bytes,fp=int(native[1]),
                            native_equals_replay=True,member_checks_passed=True,
                            selection_seconds_with_possible_jit=selection))
    t=time.perf_counter()
    candidates=[B.build(setup,kib,frac,C5) for frac in B.E5.FRACS]
    best,_=B.E5.replay_best(candidates,learn,setup,safe)
    selection=time.perf_counter()-t
    spec=C5.layout(best['cache_bytes'])
    state=C5.allocate(spec)
    native=bf_native(best['structure'].data,tail,setup.h1q,sorted_m,state,spec['buckets'],
                     spec['Q'],spec['ob'],spec['slot_bits'],spec['handbits'])
    replay=B.E5.evaluate(best,tail,setup,safe)
    assert int(native[0])==replay['fp']
    assert C5.count_member_hits(state,setup.h1m,spec['buckets'],40,spec['Q'],spec['ob'],
                               spec['slot_bits'],4)==0
    outputs.append(dict(method='BF+ReplayCache',trees=0,cache_bytes=best['cache_bytes'],
                        total_bytes=best['structure'].used_bytes,fp=int(native[0]),
                        native_equals_replay=True,member_checks_passed=True,
                        selection_seconds_with_possible_jit=selection))
    assert all(r['total_bytes']<=kib*1024 for r in outputs)
    return dict(purpose='end-to-end smoke only; generated data, not paper evidence',seed=121212,
                rows=size,members=int(y.sum()),learning_queries=n,evaluation_queries=len(tail),budget_kib=kib,
                data_sha256=hashlib.sha256(X.tobytes()+y.tobytes()+ids.tobytes()).hexdigest(),
                training_seconds=training,score_prepare_seconds=score_prepare,
                process_seconds_with_jit=time.perf_counter()-started,results=outputs,
                memory_note='Index-based variants; backend sorted member hashes excluded from filter budget',
                python=sys.version.split()[0],numpy=np.__version__,lightgbm=lgb.__version__)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,help='New JSON file; existing files are not overwritten')
    a=p.parse_args()
    if a.output and a.output.exists():p.error('output exists; use a new filename')
    result=run()
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x',encoding='utf-8') as f:f.write(text)
    print(text)

"""Five frozen-method comparisons on real, chronologically ordered HTTP requests."""
import os
for _v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[_v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(ROOT/'src'))
from data27 import save,sha
for _r in ('round5_dp','round6_bucket','round12_nomodel','round13_complete','round19_gt_fix'):
    sys.path.insert(0,str(WR/_r/'src'))
import engine5 as E5
import ra5
import ra6
import baseline as B
from summarize19 import summarize19
from leaf_scores import prefix_raw_scores
from end_to_end import model_arrays
import numpy as np
import lightgbm as lgb
from scipy.stats import rankdata
from numba import get_num_threads
from types import SimpleNamespace
import ctypes
import hashlib
import json
import time

SEEDS=(2701,2702,2703)
BUDGETS=(4,8,16)


def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def check_freeze():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['sources'].items():assert sha(BLOOM/p)==h,p
    return sha(ROOT/'plan/freeze.json')


def prepare(path,seed):
    with np.load(path,allow_pickle=False) as d:
        ids,y,X,first,trace,order,boundary=[d[k] for k in ('ids','y','X','first','trace','order','boundary')]
    u=(E5.C.splitmix64(ids^np.uint64(seed))>>np.uint64(11)).astype(float)/2**53
    early=first<int(boundary)
    split=dict(member_train=y&(u<.5),neg_train=(~y)&early&(u<.1),neg_val=(~y)&early&(u>=.1)&(u<.2))
    split['neg_test']=(~y)&~(split['neg_train']|split['neg_val'])
    assert all(split[k].any() for k in split)
    pos=np.full(len(ids),-1,np.int64);pos[split['neg_test']]=np.arange(split['neg_test'].sum())
    q=pos[trace];learn=q[(q>=0)&(order<int(boundary))];tail=q[(q>=0)&(order>=int(boundary))]
    assert len(learn)>0 and len(tail)>0
    hashes=E5.C.splitmix64(ids^np.uint64(E5.C.H1_SALT)^np.uint64(seed))
    s=SimpleNamespace(name=f'{path.stem}_{seed}',ids=ids,y=y,split=split,h1m=hashes[y],h1q=hashes[split['neg_test']],q_ids=ids[split['neg_test']])
    assert not np.intersect1d(ids[split['neg_train']|split['neg_val']],s.q_ids).size
    assert (first[split['neg_train']|split['neg_val']]<boundary).all()
    return s,X,learn,tail


def auc(y,s):
    n=int(y.sum());m=len(y)-n
    return float((rankdata(s)[y].sum()-n*(n+1)/2)/(n*m)) if n*m else None


def evaluate(c,stream,setup,safe):
    K=E5.K;spec=K.layout(c['cache_bytes']);data=K.allocate(spec)
    cnt=K.replay(stream,setup.h1q,safe,c['structure'].fp_static,data,spec['buckets'],40,spec['Q'],spec['ob'],spec['slot_bits'],4,spec['handbits'],2**62,np.empty(0,np.int64),np.empty(0,np.bool_))
    assert cnt[5]==len(stream) and cnt[6]==0
    hits=K.count_member_hits(data,setup.h1m,spec['buckets'],40,spec['Q'],spec['ob'],spec['slot_bits'],4)
    assert hits==0
    return dict(zip(('fp','hits','inserts','evictions','bypasses','processed','cutoff','occupied'),map(int,cnt))),int(hits)


def region_diagnostics(setup,scores,t,c,learn,tail):
    st=c['structure'];qr=st.q_region
    lf=np.bincount(learn,minlength=len(qr));tf=np.bincount(tail,minlength=len(qr));out=[]
    td=E5.tree(setup,scores,t);rm=E5.D.region_of_segment(st.b)[td.seg_m]
    for r in range(len(st.f)):
        m=qr==r;f=lf[m];z=tf[m]
        out.append(dict(region=r,members=int((rm==r).sum()),pool_keys=int(m.sum()),learning_requests=int(f.sum()),learning_distinct=int((f>0).sum()),
                        learning_singleton_keys=int((f==1).sum()),learning_repeat_fraction=float(1-(f>0).sum()/f.sum()) if f.sum() else None,
                        tail_requests=int(z.sum()),tail_distinct=int((z>0).sum()),tail_repeat_fraction=float(1-(z>0).sum()/z.sum()) if z.sum() else None))
    return out


def run(path,seed,output):
    freeze=check_freeze();start=time.perf_counter()
    lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));getter=lib.openblas_get_num_threads;getter.restype=ctypes.c_int
    assert getter()==get_num_threads()==1
    s,X,learn,tail=prepare(path,seed);sp=s.split;train=sp['member_train']|sp['neg_train'];H=len(tail)
    timer=time.perf_counter();model=lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),lgb.Dataset(X[train],label=s.y[train]),num_boost_round=200);train_s=time.perf_counter()-timer
    assert model.num_trees()==200,'Too few trained trees; preserve failed experiment rather than change grid'
    timer=time.perf_counter();scores=prefix_raw_scores(model,X,E5.TREES);score_s=time.perf_counter()-timer
    for t in E5.TREES:
        E5.R._MODEL_ARRAYS[s.name,t]=model_arrays(model,t)
        assert np.array_equal(scores[t],model.predict(X,raw_score=True,num_iteration=t,num_threads=1))
    s.q_score=scores[200][sp['neg_test']]
    timer=time.perf_counter();member_index=np.sort(s.h1m);safe=E5.E.CC.safe_prefix_lengths(member_index,s.h1q);index_s=time.perf_counter()-timer
    timer=time.perf_counter();lm=summarize19(learn);summary_s=time.perf_counter()-timer
    # Warm the deployed BF, DP and CLOCK kernels outside reported selection intervals.
    timer=time.perf_counter();B.build(s,4,.1,E5.K);E5.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.)
    toy=B.build(s,4,0.,E5.K);evaluate(toy,learn[:2],s,safe);jit_s=time.perf_counter()-timer
    held=(s.y&~sp['member_train'])|sp['neg_test']
    features=X.view(np.dtype((np.void,X.dtype.itemsize*X.shape[1]))).ravel()
    overlap=np.intersect1d(features[s.y],features[sp['neg_test']])
    out=dict(status='running',dataset=path.stem,seed=seed,freeze_sha256=freeze,input_sha256=sha(path),members=len(s.h1m),negative_pool=len(s.h1q),
             train_members=int(sp['member_train'].sum()),train_negatives=int(sp['neg_train'].sum()),validation_negatives=int(sp['neg_val'].sum()),
             learning_queries=len(learn),tail_queries=H,learning_distinct=len(np.unique(learn)),tail_distinct=len(np.unique(tail)),
             learning_sha256=ah(learn),tail_sha256=ah(tail),model_training_s=train_s,score_preparation_s=score_s,index_preparation_s=index_s,learning_summary_s=summary_s,jit_warm_s=jit_s,
             model_sha256=hashlib.sha256(model.model_to_string().encode()).hexdigest(),native_threads=1,
             exact_feature_overlap_vectors=len(overlap),negative_keys_sharing_features_with_members=int(np.isin(features[sp['neg_test']],features[s.y]).sum()),
             auc_by_tree={str(t):auc(s.y[held],scores[t][held]) for t in E5.TREES},backend_index_payload_bytes=member_index.nbytes,backend_index_physical_bytes=sys.getsizeof(member_index),rows=[])
    for kib in BUDGETS:
        timer=time.perf_counter();zeros=[E5.build(s,scores,t,kib,0.) for t in E5.TREES if E5.tree(s,scores,t).fixed<kib*1024];g=E5.gama(zeros);g_s=time.perf_counter()-timer
        timer=time.perf_counter();cands=E5.candidates(s,scores,kib);grid_build_s=time.perf_counter()-timer
        timer=time.perf_counter();replay,_=E5.replay_best(cands,learn,s,safe);replay_s=time.perf_counter()-timer
        timer=time.perf_counter();glob,gi=ra5.select(s,scores,lm,kib,H,ra5.Config(mode='global',new_mix=0.));global_s=time.perf_counter()-timer
        timer=time.perf_counter();ra,ri=ra6.select6(s,scores,lm,kib,H);ra_s=time.perf_counter()-timer
        timer=time.perf_counter();bf_cands=[B.build(s,kib,f,E5.K) for f in E5.FRACS];bf_build_s=time.perf_counter()-timer
        timer=time.perf_counter();bf,_=E5.replay_best(bf_cands,learn,s,safe);bf_replay_s=time.perf_counter()-timer
        choices=[('Gama',g,g_s,{}),('Replay',replay,grid_build_s+replay_s,dict(grid_build_s=grid_build_s,learning_replay_s=replay_s,candidates=len(cands))),
                 ('RA-global',glob,summary_s+global_s,gi),('RA-PLBF-GT19',ra,summary_s+ra_s,ri),('BF+Cache',bf,bf_build_s+bf_replay_s,dict(grid_build_s=bf_build_s,learning_replay_s=bf_replay_s,candidates=len(bf_cands)))]
        for method,c,select_s,info in choices:
            timer=time.perf_counter();result,member_fn=evaluate(c,tail,s,safe);eval_s=time.perf_counter()-timer;st=c['structure']
            assert st.used_bytes==st.model_bytes+st.metadata_bytes+st.array_overhead_bytes+st.filter_bytes+c['cache_bytes']<=kib*1024
            row=dict(method=method,budget_kib=kib,trees=c['trees'],cache_frac=c['frac'],**result,total_bytes=int(st.used_bytes),unused_bytes=int(kib*1024-st.used_bytes),
                     model_payload_bytes=int(st.model_bytes),bf_payload_bytes=int(st.filter_bytes),metadata_bytes=int(st.metadata_bytes),array_overhead_bytes=int(st.array_overhead_bytes),cache_physical_bytes=c['cache_bytes'],
                     backend_member_index_payload_bytes=member_index.nbytes,backend_member_index_physical_bytes=sys.getsizeof(member_index),member_fn=member_fn,
                     build_and_select_s=select_s,tail_replay_s=eval_s,selection_info=info,static_flags_sha256=ah(st.fp_static),
                     region_diagnostics=region_diagnostics(s,scores,c['trees'],c,learn,tail) if c['trees'] else None)
            out['rows'].append(row);save(output,out)
            print(f'RESULT {path.stem} seed={seed} {kib}KiB {method} t={c["trees"]} frac={c["frac"]}: FP={result["fp"]} select={select_s:.3f}s',flush=True)
    assert len(out['rows'])==15;check_freeze();out.update(status='complete',wall_s=time.perf_counter()-start);save(output,out)
    print(f'COMPLETE {path.stem} {seed}',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('seed',type=int,choices=SEEDS);p.add_argument('output',type=Path);a=p.parse_args()
    assert not a.output.exists(),'Refuse result overwrite'
    try:run(a.input,a.seed,a.output)
    except Exception as e:
        save(a.output.with_suffix('.error.json'),dict(status='failed',error=repr(e)));raise

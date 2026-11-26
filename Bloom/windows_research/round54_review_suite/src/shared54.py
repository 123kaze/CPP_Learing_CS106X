"""Read only prepared inputs; new output paths, exact full-key caches and frozen selectors."""
import os
for k in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
import sys,json,time,hashlib,resource
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
for r in ('round53_index_free_recheck_v3','round17_zerotree','round51_training_stability','round42_raw_key_sqlite'):
    sys.path.insert(0,str(WR/r/'src'))
import common53 as C53
import cache53 as K53
import zero17 as Z
import stability51 as S51
import online42 as O42
from common53 import E5,RA,C,np,sha,ah,save,summarize19
import pandas as pd
import lightgbm as lgb
from numba import njit
W=O42.W;R6=Z.ra6;B=O42.B
TCP=json.loads((WR/'round11_tcp/results/datasets.json').read_text())
CMATRIX={'url':(64,128),'mawi2024_flow':(16,32),'clark':(8,16)}
DMATRIX={'url':128,'mawi2024_flow':32,'clark':16,'sis':1343}
KEYROOT=WR/'round53_index_free_recheck_v4/cache'
CACHE=WR/'round2_backlog/cache'

class Exact(K53.Cache):
    def __init__(self,width):
        assert width in (8,9,32,33,128);self.width=width

@contextmanager
def scope(cache):
    old=E5.build
    def build(*a,**kw):
        c=old(*a,**kw)
        if c is not None and hasattr(c['structure'],'q_region'):del c['structure'].q_region
        return c
    with C53.no_index(),K53.layout_scope(cache):
        E5.build=build
        try:yield
        finally:E5.build=old


def check():
    frozen=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in frozen['sources'].items():assert sha(BLOOM/p)==h,p


def paths(ds):
    if ds=='clark':return [WR/'round36_http_qualification/cache/clarknet.npz',WR/'round41_exact_key_budget/cache/raw_keys.npz']
    if ds=='sis':return [WR/'round50_sis_fullfile_diagnostics/cache/sis_fullfile.npz']
    ps=[CACHE/ds/name for name in ('data.npz','scores.npz','gama_scores.npz','model200.txt')]
    if ds.endswith('_flow'):ps.append(CACHE/ds/'trace.npy')
    source=ds.replace('_tcp_flow','_flow')
    ps.append(KEYROOT/f'{source}.npz')
    if '_tcp_' in ds:ps.append(CACHE/source/'data.npz')
    return ps


def load(ds,seed=0):
    t=time.perf_counter();f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p in paths(ds):assert sha(p)==f['inputs'][str(p.relative_to(BLOOM))],str(p)
    timings={};meta=dict(dataset=ds,seed=seed)
    if ds in ('clark','sis'):
        if ds=='clark':
            s,X,learn,tail=W.prepare(paths(ds)[0],seed)
            with np.load(paths(ds)[1],allow_pickle=False) as a:blob,off=a['blob'],a['offsets']
        else:
            ids,y,X,sp,learn,tail,_=S51.P.load(seed)
            hashes=C.splitmix64(ids^np.uint64(C.H1_SALT)^np.uint64(seed))
            s=SimpleNamespace(name=f'sis54_{seed}',ids=ids,y=y,split=sp,h1m=hashes[y],h1q=hashes[sp['neg_test']],q_ids=ids[sp['neg_test']])
            with np.load(paths(ds)[0],allow_pickle=False) as a:blob,off=a['blob'],a['offsets']
        timings['load_s']=time.perf_counter()-t;t=time.perf_counter()
        train=s.split['member_train']|s.split['neg_train'];weights=S51.weights(s.y[train]) if ds=='sis' else None
        model=lgb.train(S51.params(seed,'balanced_clip' if ds=='sis' else 'original'),lgb.Dataset(X[train],label=s.y[train],weight=weights),num_boost_round=200)
        assert model.num_trees()==200
        timings['training_s']=time.perf_counter()-t;t=time.perf_counter();scores=W.prefix_raw_scores(model,X,E5.TREES)
        for tr in E5.TREES:E5.R._MODEL_ARRAYS[s.name,tr]=W.model_arrays(model,tr)
        timings['score_and_model_arrays_s']=time.perf_counter()-t;s.q_score=scores[200][s.split['neg_test']];width=128
    else:
        if '_tcp_' in ds:C.DATASETS[ds]=dict(member_train=.5,neg_cuts=(.1,.2))
        with np.load(CACHE/ds/'data.npz',allow_pickle=False) as a:ids,y,X=a['ids'],a['y'],a['X']
        sp=C.make_split(ids,y,ds);hashes=C.splitmix64(ids^np.uint64(C.H1_SALT))
        with np.load(CACHE/ds/'scores.npz',allow_pickle=False) as a:score=a['score']
        s=SimpleNamespace(name=ds,ids=ids,y=y,split=sp,h1m=hashes[y],h1q=hashes[sp['neg_test']],q_ids=ids[sp['neg_test']],q_score=score[sp['neg_test']])
        scores=C53.Scores(ds);model=lgb.Booster(model_file=str(CACHE/ds/'model200.txt'))
        for tr in E5.TREES:E5.R._MODEL_ARRAYS[s.name,tr]=W.model_arrays(model,tr)
        source=ds.replace('_tcp_flow','_flow')
        with np.load(KEYROOT/f'{source}.npz',allow_pickle=False) as a:blob,off=a['blob'],a['offsets']
        if '_tcp_' in ds:
            with np.load(CACHE/source/'data.npz',allow_pickle=False) as a:full_y=a['y']
            width=32 if ds.startswith('caida') else 8;full=blob.reshape(-1,width+1);keys=full[~full_y,:width].copy()
            assert len(keys)==len(ids);nb=width//2
            text=[str(int.from_bytes(k[:nb],'little'))+'>'+str(int.from_bytes(k[nb:],'little')) for k in keys]
            hid=pd.util.hash_pandas_object(pd.Series(text),index=False).to_numpy(np.uint64)
            assert np.array_equal(hid,ids),'Full TCP raw identity/order mismatch'
            blob=keys.ravel().copy();off=np.arange(len(ids)+1,dtype=np.int64)*width
        else:width=9 if ds.endswith('_flow') else 128
        if ds.endswith('_flow'):base=C.load_flow_trace(s)
        else:base=E5.base_stream(s,'zipf1.0-全部',('zipf',None,1.),0,10000000)
        n=len(base)//4;learn,tail=base[:n],base[n:]
        timings.update(load_s=time.perf_counter()-t,training_s=None,score_and_model_arrays_s=None)
    assert len(off)==len(s.ids)+1 and off[-1]==len(blob)
    qi=np.flatnonzero(s.split['neg_test']);mi=np.flatnonzero(s.y);cache=Exact(width)
    evaluator=K53.Evaluator(cache,s,blob,off,qi)
    t=time.perf_counter()
    for tr in E5.TREES:E5.tree(s,scores,tr)
    timings['tree_prepare_s']=time.perf_counter()-t
    t=time.perf_counter();lm=summarize19(learn);timings['summary_s']=time.perf_counter()-t
    t=time.perf_counter()
    with scope(cache):
        c=B.build(s,4,0.,cache);evaluator.evaluate(c,learn[:2]);E5.build(s,scores,1,4,0.)
        sp=cache.layout(4096);a=cache.allocate(sp);K53.member_hits(a,s.h1m[:1],blob,off,mi[:1],sp['buckets'],width)
    timings['jit_s']=time.perf_counter()-t
    meta.update(members=len(mi),negative_pool=len(qi),learning_queries=len(learn),tail_queries=len(tail),learn_sha=ah(learn),tail_sha=ah(tail),width=width,raw_input_payload_bytes=blob.nbytes+off.nbytes,feature_payload_bytes=X.nbytes,training_scope='new measured 200-tree training' if ds in ('clark','sis') else 'frozen model and scores reused; no new training timing',timings=timings)
    return SimpleNamespace(ds=ds,seed=seed,s=s,X=X,scores=scores,model=model,blob=blob,off=off,qi=qi,mi=mi,cache=cache,e=evaluator,learn=learn,tail=tail,lm=lm,meta=meta)


def timed(fn,*a,**k):
    t=time.perf_counter();v=fn(*a,**k);return v,time.perf_counter()-t


def ledger(c):
    st=c['structure'];parts={k:int(getattr(st,k)) for k in ('model_bytes','filter_bytes','metadata_bytes','array_overhead_bytes')}
    assert sum(parts.values())+c['cache_bytes']==st.used_bytes<=st.budget_bytes
    return dict(deployment_M=st.budget_bytes,deployment_used_bytes=st.used_bytes,required_backend_member_index_bytes=0,cache_bytes=c['cache_bytes'],slots=c['slots'],**parts)


def result(d,c,stream,method,selection_s):
    (cnt,state),replay_s=timed(d.e.evaluate,c,stream);sp=d.cache.layout(c['cache_bytes']);before=ah(state)
    hits=K53.member_hits(state,d.s.h1m,d.blob,d.off,d.mi,sp['buckets'],d.cache.width)
    assert hits==0 and before==ah(state) and cnt[5]==len(stream) and cnt[6]==0
    return dict(method=method,trees=c['trees'],frac=c['frac'],fp=int(cnt[0]),hits=int(cnt[1]),bypass=int(cnt[4]),query_count=len(stream),member_fn=0,flags_sha=ah(c['structure'].fp_static),cache_sha=before,selection_build_s=selection_s,reference_replay_s=replay_s,**ledger(c))


def pick(d,kib,learn=None,H=None):
    learn=d.learn if learn is None else learn;H=len(d.tail) if H is None else H
    lm,summary_s=timed(summarize19,learn)
    with scope(d.cache):
        grid,grid_s=timed(E5.candidates,d.s,d.scores,kib)
        (rep,rep_log),rep_s=timed(d.e.best,grid,learn)
        g=E5.gama(grid)
        (ra,ri),ra_s=timed(R6.select6,d.s,d.scores,lm,kib,H)
        (glob,gi),glob_s=timed(RA.select,d.s,d.scores,lm,kib,H,RA.Config(mode='global',new_mix=0.))
        bgrid,b_s=timed(lambda:[B.build(d.s,kib,f,d.cache) for f in E5.FRACS])
        (bf,bf_log),br_s=timed(d.e.best,bgrid,learn)
    return dict(Gama=(g,grid_s),Replay=(rep,grid_s+rep_s),RA6=(ra,summary_s+ra_s),RAglobal=(glob,summary_s+glob_s),BF=(bf,b_s+br_s),PlainBF=(bgrid[0],b_s/len(bgrid))),dict(lm=lm,summary_s=summary_s,grid=grid,bgrid=bgrid,grid_s=grid_s,bfgrid_s=b_s,replay_log=rep_log,bf_log=bf_log,ra_info=ri)

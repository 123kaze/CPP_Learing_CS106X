"""Full archived case identity; only new exact-key results and bounded host workspace."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys,time,json,csv,resource,hashlib
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round53_index_free_recheck_v3/src'))
import common53 as O
import cache53 as K
from common53 import E5,RA,C,np,sha,ah,save
from summarize19 import summarize19
import ra6 as R6
import baseline as BF
import stacked_full as STACK
RAW=WR/'round53_index_free_recheck_v4/cache'
MAIN=('Gama','Gama+10%','Replay','RA-stage1','RA-global','RA6-top3','RA6','RA6-top10','PlainBF','BF+Exact')
ABLS={'noRepeat':RA.Config(mode='norepeat',new_mix=0.),'noSA':RA.Config(setassoc=False,new_mix=0.),'noGT':RA.Config(gt=False,new_mix=0.),'mix0.5':RA.Config(new_mix=.5),'mix1':RA.Config(new_mix=1.)}


def readcsv(p):
    with p.open() as f:return list(csv.DictReader(f))


def freeze_check(ds=None):
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['sources'].items():assert sha(BLOOM/p)==h,p
    if ds:
        for p in input_paths(ds):assert sha(p)==f['inputs'][str(p.relative_to(BLOOM))],str(p)
    return f


def input_paths(ds):
    paths=[C.CACHE/ds/n for n in ('data.npz','scores.npz','gama_scores.npz','model200.txt')]+[RAW/f'{ds}.npz']
    if ds.endswith('_flow'):paths.append(C.CACHE/ds/'trace.npy')
    return paths


def case_manifest():return json.loads((ROOT/'plan/cases.json').read_text())


def width(ds):return 8 if ds in ('cod','caida') else 33 if ds=='caida_flow' else 9 if ds.endswith('_flow') else 128


@contextmanager
def scope(cache):
    old=E5.build
    def build(*a,**kw):
        c=old(*a,**kw)
        if c is not None and hasattr(c['structure'],'q_region'):del c['structure'].q_region
        return c
    with O.no_index(),K.layout_scope(cache):
        E5.build=build
        try:yield
        finally:E5.build=old


def load(ds):
    t=time.perf_counter();freeze_check(ds)
    with np.load(C.CACHE/ds/'data.npz',allow_pickle=False) as a:ids,y=a['ids'],a['y']
    split=C.make_split(ids,y,ds)
    with np.load(C.CACHE/ds/'scores.npz',allow_pickle=False) as a:score=a['score']
    h=C.splitmix64(ids^np.uint64(C.H1_SALT));s=SimpleNamespace(name=ds,ids=ids,y=y,split=split,h1m=h[y],h1q=h[split['neg_test']],q_ids=ids[split['neg_test']],q_score=score[split['neg_test']])
    with np.load(RAW/f'{ds}.npz',allow_pickle=False) as a:blob,off=a['blob'],a['offsets']
    assert len(off)==len(ids)+1 and off[-1]==len(blob)
    qi=np.flatnonzero(split['neg_test']);mi=np.flatnonzero(y);cache=K.Cache(width(ds));scores=O.Scores(ds);e=K.Evaluator(cache,s,blob,off,qi)
    loading=time.perf_counter()-t;t=time.perf_counter()
    for tr in E5.TREES:E5.tree(s,scores,tr)
    tree_s=time.perf_counter()-t;t=time.perf_counter()
    with scope(cache):
        c=BF.build(s,4,0,cache);e.evaluate(c,np.zeros(1,np.int64));E5.build(s,scores,1,4,0.)
        sp=cache.layout(4096);K.member_hits(cache.allocate(sp),s.h1m[:1],blob,off,mi[:1],sp['buckets'],cache.width)
    return SimpleNamespace(s=s,scores=scores,blob=blob,off=off,qi=qi,mi=mi,cache=cache,e=e,meta=dict(dataset=ds,members=len(mi),queries=len(qi),width=cache.width,input_read_s=loading,tree_prepare_s=tree_s,jit_s=time.perf_counter()-t,raw_key_payload=blob.nbytes,raw_key_offsets=off.nbytes,member_index_required_bytes=0,training_and_scoring='frozen input reuse; no fresh training timing'))


def timed(fn,*args,**kw):
    t=time.perf_counter();out=fn(*args,**kw);return out,time.perf_counter()-t


def tail_for(c,name,tail,seed):return E5.tail_for(c,name,tail,seed)


def evaluate(d,c,tail,warm=None):
    sp=d.cache.layout(c['cache_bytes']);state=d.cache.allocate(sp);start=time.perf_counter();warm_s=0.
    args=(d.s.h1q,d.blob,d.off,d.qi,c['structure'].fp_static,state,sp['buckets'],d.cache.width,2**62)
    if warm is not None:K.replay(warm,*args);warm_s=time.perf_counter()-start;start=time.perf_counter()
    cnt=K.replay(tail,*args);seconds=time.perf_counter()-start;before=ah(state);start=time.perf_counter()
    hits=K.member_hits(state,d.s.h1m,d.blob,d.off,d.mi,sp['buckets'],d.cache.width)
    assert hits==0 and before==ah(state) and cnt[5]==len(tail) and cnt[6]==0
    return dict(fp=int(cnt[0]),hits=int(cnt[1]),inserts=int(cnt[2]),evictions=int(cnt[3]),bypass=int(cnt[4]),cache_sha=before,member_fn=0,tail_replay_s=seconds,learning_warm_s=warm_s,member_check_s=time.perf_counter()-start)


def ledger(c):
    st=c['structure'];parts={key:int(getattr(st,key)) for key in ('model_bytes','filter_bytes','metadata_bytes','array_overhead_bytes')}
    assert sum(parts.values())+c['cache_bytes']==st.used_bytes<=st.budget_bytes
    return dict(total_bytes=int(st.used_bytes),budget_bytes=int(st.budget_bytes),cache_bytes=c['cache_bytes'],cache_slots=c['slots'],member_index_bytes=0,**parts)


@contextmanager
def slot_cost(cache):
    old=RA.ra4.slot_bits
    def bits(slots):
        # Target integer number of full 4-way buckets; charge actual headers as well.
        nb=max(1,int(np.ceil(max(0,slots)/4)));used=K.ARRAY_HEADER+K.HEAD+(4*(cache.width+4)+1)*nb
        return 8*used/(4*nb)
    RA.ra4.slot_bits=bits
    try:yield
    finally:RA.ra4.slot_bits=old


def table_variant(d,lm,kib,H):
    start=time.perf_counter();best=None
    with slot_cost(d.cache):
        for tr in E5.TREES:
            td=E5.tree(d.s,d.scores,tr)
            if td.fixed>=kib*1024:continue
            pop=RA.population(lm,td,H,RA.Config(new_mix=0.));eps,pred,need,j=RA.ra4.solve_table(pop,(kib*1024-td.fixed)*8)
            if best is None or (pred,tr)<best[0]:best=(pred,tr),td,pop,need,j
    (pred,tr),td,pop,need,j=best;nb=int(need//4);cb=K.ARRAY_HEADER+K.HEAD+nb*(4*(d.cache.width+4)+1) if nb else 0
    if cb>=kib*1024-td.fixed:cb=0
    slots=d.cache.layout(cb)['slots'];assert slots==4*nb if cb else slots==0
    c=E5.build(d.s,d.scores,tr,kib,cb/(kib*1024),weights=RA.dp_weights(pop,pop.Mg[j],td),cache_bytes=cb,slots=slots)
    return c,dict(predicted_fp=float(pred),selection_build_s=time.perf_counter()-start,exact_layout_adapter=True)

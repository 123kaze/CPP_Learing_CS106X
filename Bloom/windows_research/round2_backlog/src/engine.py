"""Corrected physical-budget runtime; no RA-PLBF or C-method design."""
from pathlib import Path
import sys,time,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'src'))
import prepare_datasets as D
import runtime as R
import numpy as np
from types import SimpleNamespace
from numba import njit
import fast_cache as F
import compact_cache as CC
import run_experiments as OLD
from exp9_fp_stream_controller import BinMemo,fp_stream_misses
C=R.C
FRACS=(0.,.001,.002,.005,.01,.015,.02,.05,.1,.2,.3,.4,.6)
BUDGETS={'cod':(256,1024),'caida':(128,256,1024),'shalla':(256,1024,2048),
         'url':(64,128,256),'caida_flow':(16,24,32),'mawi2021_flow':(16,24,32),'mawi2022_flow':(16,24,32)}
TREE_BYTES={}
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def load(ds):
    s=R.load_setup(ds)
    scores=R.scores_for(s)
    safe=CC.safe_prefix_lengths(s.member_hashes,s.h1q)
    return s,scores,safe

def allocated(requested,policy='clock',prefix=40,ways=4,admit=1):
    if admit==2:
        secondary=256*9+2*F.ARRAY_HEADER
        if requested<secondary+256:return 0
        return secondary+F.layout(requested-secondary,prefix,policy,ways)['allocated_bytes']
    return F.layout(requested,prefix,policy,ways)['allocated_bytes']

def build(setup,scores,t,kib,f,policy='clock',prefix=40,ways=4,admit=1):
    requested=int(kib*1024*f)
    cache=allocated(requested,policy,prefix,ways,admit)
    st=R.structure(setup,scores,t,kib*1024,cache,sketch_bytes=0)
    if st is None:return None
    return dict(trees=t,frac=float(f),requested_cache_bytes=requested,cache_bytes=cache,
                policy=policy,prefix_bits=prefix,ways=ways,admit=admit,structure=st)

def build_plain(setup,kib,f):
    cache=allocated(int(kib*1024*f))
    metadata=17+16 # kind:uint8, m/k:int64, off two int64; cuts is empty.
    overhead=6*F.ARRAY_HEADER
    payload=kib*1024-cache-metadata-overhead
    if payload<1:return None
    bits=np.zeros(payload,np.uint8);m=np.array([payload*8],np.int64)
    k=np.array([max(1,min(32,round(payload*8/len(setup.h1m)*np.log(2))))],np.int64)
    off=np.array([0,payload*8],np.int64);kind=np.array([C.BF],np.uint8)
    R.packed_build(setup.h1m,np.zeros(len(setup.h1m),np.int32),off,m,k,bits)
    assert R.packed_query(setup.h1m,np.zeros(len(setup.h1m),np.int32),kind,off,m,k,bits).all()
    fp=R.packed_query(setup.h1q,np.zeros(len(setup.h1q),np.int32),kind,off,m,k,bits)
    est=float(C.bf_fpr(np.array([payload*8/len(setup.h1m)]))[0])
    st=SimpleNamespace(trees=0,cuts=np.empty(0),kind=kind,bf_off=off,m=m,k=k,bits=bits,
                       fp_static=fp,est_fpr=est,model_bytes=0,metadata_bytes=metadata,
                       array_overhead_bytes=overhead,filter_bytes=payload,cache_bytes=cache,
                       sketch_bytes=0,used_bytes=kib*1024,budget_bytes=kib*1024,model_arrays=None)
    return dict(trees=0,frac=float(f),requested_cache_bytes=int(kib*1024*f),cache_bytes=cache,
                policy='clock',prefix_bits=40,ways=4,admit=1,structure=st)

def candidates(setup,scores,kib,fracs=FRACS):
    values=[]
    for t in R.GAMA_TREES:
        for f in fracs:
            c=build(setup,scores,t,kib,f)
            if c is not None:values.append(c)
    return values

def measure(learn,setup,base):return OLD.measure(learn,setup,base.fp_static)

def rank(cands,stats,base,Qtail,learn_n,bins):
    p0=max(base.est_fpr,1e-12);nu=max(stats['N_eff'],stats['W']/p0)
    zero={c['trees']:c['structure'].est_fpr for c in cands if c['frac']==0}
    scored=[]
    for c in cands:
        pt=zero[c['trees']];p=c['structure'].est_fpr
        if stats['QF']>=100:w=stats['W']*pt/p0;qf=stats['QF']*Qtail/learn_n*pt/p0
        else:w=nu*pt;qf=Qtail*pt
        dp=max(0.,p-pt)
        slots=F.layout(c['cache_bytes'],c['prefix_bits'],c['policy'],c['ways'])['slots']
        predicted=fp_stream_misses(w+nu*dp,stats['s'],qf+Qtail*dp,slots,bins)
        scored.append((predicted,p,c['trees'],c['frac'],c))
    return sorted(scored,key=lambda x:x[:4])

def simulate(c,stream,setup,safe,limit=2**62,collect=False,placement='before'):
    return F.simulate(stream,setup.h1q,safe,c['structure'].fp_static,c['cache_bytes'],
                      policy=c['policy'],prefix_bits=c['prefix_bits'],ways=c['ways'],
                      limit=limit,admit=c['admit'],collect=collect,placement=placement)

def evaluate(c,stream,setup,safe,frequencies=None):
    """Exact final FP count; omit harmless probes only when eviction is impossible.

    At most `ways` distinct raw-FP keys in every quotient bucket guarantees no
    replacement. Non-FP queries cannot insert and can only change recency, so
    skipping them cannot change any FP decision in this special case.
    """
    if frequencies is None:frequencies=np.bincount(stream,minlength=len(setup.h1q))
    fp=c['structure'].fp_static
    keys=np.flatnonzero((frequencies>0)&fp)
    spec=F.layout(c['cache_bytes'],c['prefix_bits'],c['policy'],c['ways'])
    if c['cache_bytes']==0:
        return dict(fp=int(frequencies[keys].sum()),distinct_fp_keys=len(keys),hits=0,inserts=0,
                    evictions=0,bypasses=0,processed=len(stream),cutoff=0,occupied=0,
                    allocated_bytes=0,optimization='exact no-cache weighted count')
    # Admission probation reduces usable cache; use the actual remaining layout.
    if c['admit']==2:
        secondary=256*9+2*F.ARRAY_HEADER
        spec=F.layout(max(0,c['cache_bytes']-secondary),c['prefix_bits'],c['policy'],c['ways'])
    bounded=False
    if spec['qbits']:
        buckets=(setup.h1q[keys]>>np.uint64(64-spec['qbits'])).astype(np.int64)
        bounded=int(np.bincount(buckets,minlength=spec['buckets']).max(initial=0))<=c['ways']
    if bounded:
        events=stream[fp[stream]]
        result=simulate(c,events,setup,safe,collect=True)
        assert result['evictions']==0
        result['optimization']='exact FP-only replay: no-eviction bucket bound'
    else:
        result=simulate(c,stream,setup,safe,collect=True)
        result['optimization']='full ordered replay'
    return result

def exact_grid(ordered,learn,setup,safe,track48=True):
    start=time.perf_counter();best=None;fixed=None;records=[];memo={}
    frequencies=np.bincount(learn,minlength=len(setup.h1q))
    for item in ordered:
        c=item[-1] if isinstance(item,tuple) else item
        threshold=best[0] if best is not None else 2**62
        if track48 and c['trees']==48:threshold=max(threshold,fixed[0] if fixed is not None else 2**62)
        identity=(c['trees'],c['cache_bytes'],c['policy'],c['prefix_bits'],c['ways'],c['admit'])
        reused=identity in memo
        if reused:out=memo[identity]
        else:
            fp=c['structure'].fp_static
            keys=np.flatnonzero((frequencies>0)&fp)
            spec=F.layout(c['cache_bytes'],c['prefix_bits'],c['policy'],c['ways'])
            if c['admit']==2:
                secondary=256*9+2*F.ARRAY_HEADER
                spec=F.layout(max(0,c['cache_bytes']-secondary),c['prefix_bits'],c['policy'],c['ways'])
            bounded=False
            if spec['qbits']:
                buckets=(setup.h1q[keys]>>np.uint64(64-spec['qbits'])).astype(np.int64)
                bounded=int(np.bincount(buckets,minlength=spec['buckets']).max(initial=0))<=c['ways']
            if c['cache_bytes']==0:
                out=dict(fp=int(frequencies[keys].sum()),cutoff=0,processed=0)
            elif bounded:
                out=simulate(c,learn[fp[learn]],setup,safe,limit=threshold)
            else:out=simulate(c,learn,setup,safe,limit=threshold)
            memo[identity]=out
        key=(out['fp'],c['structure'].est_fpr,c['trees'],c['frac'],c)
        if not out['cutoff']:
            if best is None or key[:4]<best[:4]:best=key
            if c['trees']==48 and (fixed is None or key[:4]<fixed[:4]):fixed=key
        records.append(dict(trees=c['trees'],frac=c['frac'],fp_or_lower_bound=out['fp'],
                            exact=not bool(out['cutoff']),processed=0 if reused else out['processed'],identical_layout_reused=reused))
    return best[-1],fixed[-1] if fixed else None,time.perf_counter()-start,records

def workload_specs(n):
    pools={'1万':min(10000,n),'10万':min(100000,n),**({'100万':1000000} if n>1500000 else {}),'全部':None}
    return [(w[0],w[3],w[1]) for w in R.workloads(pools)]

@njit(cache=True)
def probe_replay(stream,fp,seed):
    np.random.seed(seed)
    observed=np.empty(200000,np.int64);seen=np.zeros(len(fp),np.bool_);count=0
    out=stream.copy()
    for i in range(len(out)):
        if count and np.random.random()<.1:out[i]=observed[np.random.randint(count)]
        x=out[i]
        if fp[x] and not seen[x] and count<len(observed):
            seen[x]=True;observed[count]=x;count+=1
    return out

def stream_for(setup,name,spec,family,seed,queries,gama):
    if spec is None:return C.load_flow_trace(setup)
    import exp2_repetition_cache as E2
    E2.QUERIES=queries
    stream=R.make_stream(spec,len(setup.h1q),np.random.default_rng(2000+seed),np.argsort(setup.q_score,kind='stable'))
    return probe_replay(stream,gama.fp_static,11000+seed) if family=='probe-replay' else stream

def row(c,result,ds,kib,name,seed,method,total,learn_n,selection_seconds=0):
    st=c['structure']
    assert result['allocated_bytes']==c['cache_bytes']
    assert st.used_bytes<=kib*1024
    return dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,method=method,
                queries=total,learning_queries=learn_n,evaluation_queries=total-learn_n,
                fp_tail=result['fp'],fpr=result['fp']/(total-learn_n),distinct_fp_keys=result['distinct_fp_keys'],
                trees=c['trees'],frac=c['frac'],cache_reserved_bytes=c['requested_cache_bytes'],
                cache_allocated_bytes=c['cache_bytes'],cache_returned_bytes=c['requested_cache_bytes']-c['cache_bytes'],
                model_bytes=st.model_bytes,bf_bytes=st.filter_bytes,metadata_bytes=st.metadata_bytes,
                array_overhead_bytes=st.array_overhead_bytes,sketch_deployed_bytes=0,
                actual_filter_state_bytes=st.used_bytes,sketch_learning_payload_bytes=5128 if method=='StreamModel' else 0,
                member_index_bytes=None,cache_occupied=result['occupied'],policy=c['policy'],
                selection_seconds=selection_seconds,member_false_negatives=0,cold_suffix=True)

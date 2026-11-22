"""Exact raw bytes -> hash/features/filter -> real SQL -> confirmed-negative feedback."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round41_exact_key_budget/src'))
import exact41 as E
from exact41 import E5,B,K,W,np,njit
sys.path.insert(0,str(WR/'round6_bucket/src'))
from e789 import safe_len
from data27 import lexical
import hashlib,time
EMPTY=np.empty(0,np.uint8)


@njit(cache=True)
def salted_hash(ident,seed):
    x=np.uint64(ident)^np.uint64(E5.C.H1_SALT)^np.uint64(seed)
    return E5.C.mix64(x+np.uint64(0x9E3779B97F4A7C15))


def raw_hash(key,seed):
    ident=int.from_bytes(hashlib.sha256(key).digest()[:8],'little')
    return np.uint64(salted_hash(np.uint64(ident),seed))


@njit(cache=True)
def learned_probe(x,h,feat,thr,left,right,leaf,roots,cuts,kind,off,m,k,bits):
    score=0.
    for root in roots:
        node=np.int64(root)
        while node>=0:node=np.int64(left[node] if x[feat[node]]<=thr[node] else right[node])
        score+=leaf[~node]
    g=np.searchsorted(cuts,score,side='left')
    if kind[g]==E5.C.PASS:return True
    if kind[g]!=E5.C.BF:return False
    for j in range(k[g]):
        p=off[g]+E5.C.bf_pos(h,j,m[g])
        if (bits[p>>3]>>np.uint64(p&7))&np.uint64(1)==0:return False
    return True


@njit(cache=True)
def bf_probe(h,data):
    m,k=np.int64(data[1]),np.int64(data[2])
    for j in range(k):
        p=E5.C.bf_pos(h,j,m)
        if (data[B.HEAD_WORDS+(p>>6)]>>np.uint64(p&63))&np.uint64(1)==0:return False
    return True


@njit(cache=True)
def index_probe(h,index):
    p=np.searchsorted(index,h)
    return p<len(index) and index[p]==h


class Filter:
    def __init__(self,c,s,scores,mode,index=None):
        self.mode=mode;self.seed=int(s.name.rsplit('_',1)[1]);self.index=index if mode in ('prefix','direct') else None
        self.is_learned=bool(c is not None and c['trees']);self.model=None;self.bf=None
        self.arrays={};self.spec=E.layout(0);self.cache_bytes=0
        if mode=='direct':
            assert index is not None
            self.used_bytes=sys.getsizeof(index);self.auxiliary_bytes=self.used_bytes;self.reset();return
        st=c['structure'];self.cache_bytes=c['cache_bytes']
        self.spec=E.layout(self.cache_bytes) if mode=='exact' else K.layout(self.cache_bytes)
        if self.is_learned:
            td=E5.tree(s,scores,c['trees']);reg=E5.D.region_of_segment(st.b)
            arrays=E5.R._MODEL_ARRAYS[s.name,c['trees']]
            self.model=tuple(arrays[k] for k in ('feat','thr','left','right','leaf','roots'))
            edge=E5.D.edges()[st.b[1:-1]]
            self.cuts=np.log(edge)-np.log1p(-edge)
            self.off=np.concatenate([[0],np.cumsum(st.m)]).astype(np.int64)
            self.bits=np.zeros((int(self.off[-1])+7)//8,np.uint8)
            E5.R.packed_build(s.h1m,reg[td.seg_m].astype(np.int32),self.off,st.m,st.k,self.bits)
            self.kind,self.m,self.k=st.kind,st.m,st.k
            self.arrays={**arrays,'cuts':self.cuts,'kind':self.kind,'offsets':self.off,'m':self.m,'k':self.k,'bits':self.bits}
        else:
            self.bf=st.data;self.arrays={'bf':self.bf}
        assert all(a.flags.owndata for a in self.arrays.values())
        self.array_bytes=sum(sys.getsizeof(a) for a in self.arrays.values())
        self.used_bytes=st.used_bytes
        assert self.array_bytes+self.cache_bytes<=self.used_bytes<=st.budget_bytes
        self.auxiliary_bytes=self.used_bytes+(sys.getsizeof(index) if mode=='prefix' and self.cache_bytes else 0)
        if mode=='prefix' and not self.cache_bytes:self.index=None
        self.reset()
    def reset(self):
        self.data=(E.allocate(self.spec) if self.mode=='exact' else K.allocate(self.spec)) if self.cache_bytes else EMPTY
    def probe(self,key):
        h=raw_hash(key,self.seed);v=np.frombuffer(key,np.uint8)
        if self.mode=='direct':return (1 if index_probe(h,self.index) else 0),h,v
        if self.cache_bytes:
            if self.mode=='exact':hit=E.lookup(self.data,h,v,self.spec['buckets'])
            else:
                p=self.spec;hit=K.lookup(self.data,h,p['buckets'],40,p['Q'],p['ob'],p['slot_bits'],4)
            if hit:return 2,h,v
        if self.is_learned:
            x=np.asarray(lexical(key),np.float32)
            ok=learned_probe(x,h,*self.model,self.cuts,self.kind,self.off,self.m,self.k,self.bits)
        else:ok=bf_probe(h,self.bf)
        return (1 if ok else 0),h,v
    def absent(self,h,v):
        if not self.cache_bytes:return 0
        p=self.spec
        if self.mode=='exact':return E.insert(self.data,h,v,p['buckets'])
        length=safe_len(self.index,h)
        return K.insert(self.data,h,length,p['buckets'],40,p['Q'],p['ob'],p['slot_bits'],4,p['handbits'])


def online(cursor,keys,requests,flt,accepted,found,collect=False):
    """No membership labels, precomputed hashes/features or known FP flags are accepted."""
    calls=fp=members=hits=rejects=inserts=evictions=bypass=0
    counts={} if collect else None
    start=time.perf_counter_ns()
    for j,x in enumerate(requests):
        key=keys[int(x)]
        decision,h,v=flt.probe(key) if flt is not None else (1,None,None)
        exists=False
        if decision==2:hits+=1
        elif decision==0:rejects+=1
        else:
            accepted[j]=1;calls+=1
            value=cursor.execute('SELECT v FROM kv WHERE k=?',(key,)).fetchone()
            if value is not None:
                assert len(value[0])==32;exists=True;members+=1;found[j]=1
            else:
                fp+=1
                if flt is not None:
                    action=flt.absent(h,v);inserts+=int(action>0);evictions+=int(action==2);bypass+=int(action==0)
        if collect:
            # Complete inlet negative counts. Keys are actual raw bytes, never backend-only logs.
            if not exists:counts[key]=counts.get(key,0)+1
    elapsed=time.perf_counter_ns()-start
    return dict(elapsed_ns=elapsed,ns_per_query=elapsed/len(requests),backend_calls=calls,fp=fp,members_found=members,cache_hits=hits,filter_rejects=rejects,inserts=inserts,evictions=evictions,bypasses=bypass,negative_distinct=len(counts) if collect else None,negative_count_sum=sum(counts.values()) if collect else None,negative_counter_python_bytes=sys.getsizeof(counts)+sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in counts.items()) if collect else None)


@njit(cache=True)
def reference(requests,hashes,blob,offsets,flags,member,data,mode,nb,Q,ob,sb,hb,index):
    accepted=np.zeros(len(requests),np.uint8);found=np.zeros(len(requests),np.uint8)
    for j,ix in enumerate(requests):
        x=np.int64(ix);h=hashes[x];key=blob[offsets[x]:offsets[x+1]]
        hit=False
        if nb:
            hit=E.lookup(data,h,key,nb) if mode==1 else K.lookup(data,h,nb,40,Q,ob,sb,4)
        if hit:assert not member[x];continue
        if not flags[x]:assert not member[x];continue
        accepted[j]=1
        if member[x]:found[j]=1
        elif nb:
            if mode==1:E.insert(data,h,key,nb)
            else:K.insert(data,h,safe_len(index,h),nb,40,Q,ob,sb,4,hb)
    return accepted,found

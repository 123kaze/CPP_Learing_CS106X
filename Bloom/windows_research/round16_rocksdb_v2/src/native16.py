"""Label-free probe and explicit backend-confirmed miss feedback, native kernels.

No membership labels or static FP tables are accepted by probe/feedback. Caller
must call feedback only after the synchronous backend Get has returned None.
"""
from common16 import *
import numpy as np
from numba import njit,types
from numba.experimental import jitclass
sys.path.insert(0,str(WR/'round6_bucket/src'))
import e789 as J
sys.path.insert(0,str(WR/'round12_nomodel/src'))
import baseline as BF
E5=J.E5;K=E5.K;C=E5.C

spec=[('is_bf',types.boolean),('feat',types.int16[::1]),('thr',types.float64[::1]),
      ('left',types.int16[::1]),('right',types.int16[::1]),('leaf',types.float64[::1]),('roots',types.int16[::1]),
      ('cuts',types.float64[::1]),('kind',types.int64[::1]),('off',types.int64[::1]),('m',types.int64[::1]),('k',types.int64[::1]),
      ('bits',types.uint8[::1]),('bf',types.uint64[::1]),('sorted_m',types.uint64[::1]),('state',types.uint64[::1]),
      ('B',types.int64),('Q',types.int64),('ob',types.int64),('sb',types.int64),('hb',types.int64),('last_hash',types.uint64)]


@jitclass(spec)
class Native:
    def __init__(self,is_bf,feat,thr,left,right,leaf,roots,cuts,kind,off,m,k,bits,bf,sorted_m,state,B,Q,ob,sb,hb):
        self.is_bf=is_bf;self.feat=feat;self.thr=thr;self.left=left;self.right=right;self.leaf=leaf;self.roots=roots
        self.cuts=cuts;self.kind=kind;self.off=off;self.m=m;self.k=k;self.bits=bits;self.bf=bf
        self.sorted_m=sorted_m;self.state=state;self.B=B;self.Q=Q;self.ob=ob;self.sb=sb;self.hb=hb;self.last_hash=np.uint64(0)

    def probe(self,key,x):
        z=(np.uint64(key)^np.uint64(C.H1_SALT))+np.uint64(0x9E3779B97F4A7C15)
        z=(z^(z>>np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9)
        z=(z^(z>>np.uint64(27)))*np.uint64(0x94D049BB133111EB)
        h=z^(z>>np.uint64(31));self.last_hash=h
        if self.B and K.lookup(self.state,h,self.B,40,self.Q,self.ob,self.sb,4):return 2
        if self.is_bf:
            m=np.int64(self.bf[1]);k=np.int64(self.bf[2])
            for j in range(k):
                p=C.bf_pos(h,j,m)
                if (self.bf[4+(p>>6)]>>np.uint64(p&63))&np.uint64(1)==0:return 0
            return 1
        s=0.
        for root in self.roots:
            n=np.int64(root)
            while n>=0:n=np.int64(self.left[n] if x[self.feat[n]]<=self.thr[n] else self.right[n])
            s+=self.leaf[~n]
        g=np.searchsorted(self.cuts,s,side='left')
        if self.kind[g]==int(C.PASS):return 1
        if self.kind[g]!=int(C.BF):return 0
        for j in range(self.k[g]):
            p=self.off[g]+C.bf_pos(h,j,self.m[g])
            if (self.bits[p>>3]>>np.uint8(p&7))&np.uint8(1)==0:return 0
        return 1

    def feedback(self):
        if self.B:
            return K.insert(self.state,self.last_hash,J.safe_len(self.sorted_m,self.last_hash),
                            self.B,40,self.Q,self.ob,self.sb,4,self.hb)
        return 0


KEYS=('feat','thr','left','right','leaf','roots','cuts','kind','off','m','k','bits','bf','sorted_m')


def arrays_for(setup,scores,c,is_bf):
    a={k:np.zeros(0,dtype) for dtype,keys in [(np.int16,('feat','left','right','roots')),
          (np.float64,('thr','leaf','cuts')),(np.int64,('kind','off','m','k')),
          (np.uint8,('bits',)),(np.uint64,('bf','sorted_m'))] for k in keys}
    if is_bf:a['bf']=c['structure'].data.copy()
    else:
        td=E5.tree(setup,scores,c['trees']);st=c['structure']
        a.update({k:v.copy() for k,v in E5.R._MODEL_ARRAYS[setup.name,c['trees']].items()})
        boundaries=st.b[1:-1]/J.D.N_SEG
        a['cuts']=np.log(boundaries)-np.log1p(-boundaries)
        a['kind']=st.kind.astype(np.int64);a['m']=st.m.copy();a['k']=st.k.copy()
        a['off']=np.concatenate([[0],np.cumsum(st.m)]).astype(np.int64)
        a['bits']=np.zeros(st.filter_bytes,np.uint8)
        E5.R.packed_build(setup.h1m,J.D.region_of_segment(st.b)[td.seg_m].astype(np.int32),a['off'],a['m'],a['k'],a['bits'])
    if c['cache_bytes']:a['sorted_m']=np.sort(setup.h1m)
    return a


def make_native(a,is_bf,cache_bytes):
    s=K.layout(cache_bytes)
    state=K.allocate(s)
    return Native(is_bf,*(a[k] for k in KEYS),state,s['buckets'],s['Q'],s['ob'],s['slot_bits'],s['handbits'])


@njit(cache=True)
def probe_all(native,ids,X):
    out=np.empty(len(ids),np.uint8)
    for i in range(len(ids)):out[i]=native.probe(ids[i],X[i])
    return out


@njit(cache=True)
def reference_stream(native,stream,ids,X,member_count):
    # Correctness-only oracle simulator, never used for RocksDB performance.
    fp=0
    for i in stream:
        ok=native.probe(ids[i],X[i])
        if i<member_count:assert ok==1
        elif ok==1:fp+=1;native.feedback()
    return fp

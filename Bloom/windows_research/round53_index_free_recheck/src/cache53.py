"""Exact key CLOCK, adapted from frozen exact41; schema width is explicit, never a hash fingerprint."""
import sys
from contextlib import contextmanager
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import np,E5
from numba import njit
HEAD=32; ARRAY_HEADER=sys.getsizeof(np.empty(0,np.uint8))


class Cache:
    def __init__(self,width):
        assert width in (8,9,128)
        self.width=width
    def layout(self,budget_bytes,prefix_bits=40,ways=4):
        assert ways==4 and int(budget_bytes)==budget_bytes and budget_bytes>=0
        stride=4*(self.width+4)+1
        nb=max(0,(int(budget_bytes)-ARRAY_HEADER-HEAD)//stride)
        size=ARRAY_HEADER+HEAD+stride*nb if nb else 0
        return dict(buckets=nb,slots=4*nb,allocated_bytes=size,budget_bytes=int(budget_bytes),nbytes=size-ARRAY_HEADER if nb else 0,width=self.width)
    def allocate(self,spec):
        data=np.zeros(spec['nbytes'],np.uint8)
        if spec['buckets']:
            data[:8]=np.frombuffer(b'EXACT053',np.uint8)
            data[8:16]=np.frombuffer(int(spec['buckets']).to_bytes(8,'little'),np.uint8)
            data[16:18]=np.frombuffer(self.width.to_bytes(2,'little'),np.uint8)
            assert data.flags.owndata and sys.getsizeof(data)==spec['allocated_bytes']<=spec['budget_bytes']
        return data


@njit(cache=True)
def bucket(h,nb):return np.int64(((np.uint64(h)>>np.uint64(32))*np.uint64(nb))>>np.uint64(32))


@njit(cache=True)
def lookup(data,h,key,nb,width):
    if nb==0 or len(key)>width:return False
    stride=width+4;start=HEAD+bucket(h,nb)*(4*stride+1)
    for w in range(4):
        p=start+w*stride
        if data[p+width+2]==0:continue
        n=np.int64(data[p+width])+256*np.int64(data[p+width+1])
        if n!=len(key):continue
        equal=True
        for j in range(n):
            if data[p+j]!=key[j]:equal=False;break
        if equal:data[p+width+3]=1;return True
    return False


@njit(cache=True)
def insert(data,h,key,nb,width):
    if nb==0 or len(key)>width:return 0
    stride=width+4;start=HEAD+bucket(h,nb)*(4*stride+1);chosen=-1
    for w in range(4):
        if data[start+w*stride+width+2]==0:chosen=w;break
    evicted=chosen<0
    if evicted:
        hand=np.int64(data[start+4*stride])
        for _ in range(8):
            p=start+hand*stride
            if data[p+width+3]==0:chosen=hand;break
            data[p+width+3]=0;hand=(hand+1)%4
        if chosen<0:chosen=hand
        data[start+4*stride]=(chosen+1)%4
    p=start+chosen*stride
    for j in range(width):data[p+j]=key[j] if j<len(key) else 0
    data[p+width]=len(key)%256;data[p+width+1]=len(key)//256
    data[p+width+2]=1;data[p+width+3]=1
    return 2 if evicted else 1


@njit(cache=True)
def replay(stream,hashes,blob,offsets,indices,flags,data,nb,width,limit):
    # queries are negatives in this offline reference; no backend timing claim
    cnt=np.zeros(7,np.int64)  # fp,hits,inserts,evictions,bypasses,processed,cutoff
    for ix in stream:
        x=np.int64(ix);i=indices[x];key=blob[offsets[i]:offsets[i+1]]
        cnt[5]+=1
        if lookup(data,hashes[x],key,nb,width):cnt[1]+=1
        elif flags[x]:
            cnt[0]+=1
            if cnt[0]>limit:cnt[6]=1;return cnt
            a=insert(data,hashes[x],key,nb,width)
            cnt[2]+=np.int64(a>0);cnt[3]+=np.int64(a==2);cnt[4]+=np.int64(a==0)
    return cnt


@njit(cache=True)
def member_hits(data,hashes,blob,offsets,indices,nb,width):
    hits=0
    for j in range(len(indices)):
        i=indices[j]
        if lookup(data,hashes[j],blob[offsets[i]:offsets[i+1]],nb,width):hits+=1
    return hits


@contextmanager
def layout_scope(cache):
    old=E5.K;E5.K=cache
    try:yield
    finally:E5.K=old


class Evaluator:
    """Host-only replay input. Deployment cache stores full bytes, not pointers into these arrays."""
    def __init__(self,cache,s,blob,offsets,qi):
        self.cache,self.s,self.blob,self.offsets,self.qi=cache,s,blob,offsets,qi
    def evaluate(self,c,stream,limit=2**62):
        spec=self.cache.layout(c['cache_bytes']);data=self.cache.allocate(spec)
        cnt=replay(stream,self.s.h1q,self.blob,self.offsets,self.qi,c['structure'].fp_static,data,spec['buckets'],self.cache.width,limit)
        assert spec['allocated_bytes']==c['cache_bytes']
        return cnt,data
    def best(self,cands,stream):
        freq=np.bincount(stream,minlength=len(self.s.h1q));best=None;records=[]
        for c in sorted(cands,key=lambda c:c['structure'].est_fpr):
            st=c['structure'];limit=best[0][0] if best else 2**62
            if not c['cache_bytes']:fp,cut=int(freq[st.fp_static].sum()),False
            else:
                cnt,_=self.evaluate(c,stream,limit);fp,cut=int(cnt[0]),bool(cnt[6])
            records.append(dict(trees=c['trees'],frac=c['frac'],fp=fp,cutoff=cut))
            if not cut:
                key=(fp,st.est_fpr,c['trees'],c['frac'])
                if best is None or key<best[0]:best=key,c
        assert best is not None
        return best[1],records

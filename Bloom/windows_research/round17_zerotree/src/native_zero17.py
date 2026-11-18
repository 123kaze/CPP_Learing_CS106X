"""Deployable zero-tree path: BF/cache only, no model or feature inputs.

Keys are represented by the same h1 uint64 hashes as the frozen engine. Admission
is separate: call feedback_absent only after an authoritative store returned absent.
"""
import sys
import numpy as np
from numba import njit
from zero17 import BF,E5
C5=BF.CACHES['index'];F64=BF.CACHES['fp64']


@njit(cache=True)
def probe(data,state,hashes,B,Q,ob,sb,hb,fp64):
    result=np.empty(len(hashes),np.uint8) # 0=BF rejection, 1=accepted, 2=cache hit
    m,k=np.int64(data[1]),np.int64(data[2])
    for i,h in enumerate(hashes):
        hit=False
        if B:
            hit=(F64.lookup(state,h,B,64,Q,ob,sb,4) if fp64 else C5.lookup(state,h,B,40,Q,ob,sb,4))
        if hit:result[i]=2;continue
        ok=True
        for j in range(k):
            p=BF.C.bf_pos(h,j,m)
            if (data[BF.HEAD_WORDS+(p>>6)]>>np.uint64(p&63))&np.uint64(1)==0:ok=False;break
        result[i]=1 if ok else 0
    return result


@njit(cache=True)
def feedback(state,h,sorted_members,B,Q,ob,sb,hb,fp64):
    if not B:return 0
    if fp64:return F64.insert(state,h,B,64,Q,ob,sb,4,hb)
    # Frozen safe-prefix insertion: complete member hash index, no trained model.
    pos=np.searchsorted(sorted_members,h);length=1
    for i in (pos-1,pos):
        if 0<=i<len(sorted_members):
            x=sorted_members[i]^h
            if x==0:return 0
            leading=0;bit=np.uint64(1)<<np.uint64(63)
            while (x&bit)==0:leading+=1;bit>>=np.uint64(1)
            length=max(length,leading+1)
    return C5.insert(state,h,length,B,40,Q,ob,sb,4,hb)


class ZeroTreeFilter:
    def __init__(self,data,cache_bytes,mode,member_hashes=None):
        if mode not in BF.CACHES:raise ValueError('Unknown cache mode')
        self.data=np.asarray(data,np.uint64).copy()
        if len(self.data)<BF.HEAD_WORDS or int(self.data[0])!=BF.MAGIC:raise ValueError('Invalid BF buffer')
        if int(self.data[1])!=(len(self.data)-BF.HEAD_WORDS)*64 or int(self.data[2])<1:raise ValueError('Invalid BF layout')
        self.mode=mode;cache=BF.CACHES[mode];self.spec=cache.layout(cache_bytes)
        self.state=cache.allocate(self.spec)
        if self.spec['buckets'] and mode=='index':
            if member_hashes is None:raise ValueError('Verified-prefix admission requires member index')
            self.sorted_members=np.sort(np.asarray(member_hashes,np.uint64))
        else:self.sorted_members=np.empty(0,np.uint64)
        self.deployment_bytes=sys.getsizeof(self.data)+self.spec['allocated_bytes']
        self.external_index_bytes=self.sorted_members.nbytes

    def probe_hashes(self,hashes):
        s=self.spec
        return probe(self.data,self.state,np.asarray(hashes,np.uint64),s['buckets'],s['Q'],s['ob'],s['slot_bits'],s['handbits'],self.mode=='fp64')

    def feedback_absent(self,h):
        s=self.spec
        return feedback(self.state,np.uint64(h),self.sorted_members,s['buckets'],s['Q'],s['ob'],s['slot_bits'],s['handbits'],self.mode=='fp64')


@njit(cache=True)
def verify_negative_stream(data,state,stream,hashes,sorted_members,B,Q,ob,sb,hb,fp64):
    """Correctness-only native traversal of a known-negative test stream, not live admission."""
    m,k=np.int64(data[1]),np.int64(data[2]);fps=0;hits=0
    for i in stream:
        h=hashes[i]
        hit=False
        if B:hit=F64.lookup(state,h,B,64,Q,ob,sb,4) if fp64 else C5.lookup(state,h,B,40,Q,ob,sb,4)
        if hit:hits+=1;continue
        ok=True
        for j in range(k):
            p=BF.C.bf_pos(h,j,m)
            if (data[BF.HEAD_WORDS+(p>>6)]>>np.uint64(p&63))&np.uint64(1)==0:ok=False;break
        if ok:
            fps+=1
            feedback(state,h,sorted_members,B,Q,ob,sb,hb,fp64)
    return fps,hits

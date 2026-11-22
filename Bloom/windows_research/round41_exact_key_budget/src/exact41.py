"""Exact raw-key CLOCK: no fingerprint-only hit, index or key-dictionary reference."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'): os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; WR=ROOT.parent; BLOOM=WR.parent
sys.path.insert(0,str(WR/'round27_http_real/src'))
import worker27 as W
import numpy as np
from numba import njit
from contextlib import contextmanager
E5=W.E5; B=W.B; RA=W.ra5; R6=W.ra6
K=E5.K
KEY_BYTES=128; SLOT_BYTES=132; BUCKET_BYTES=4*SLOT_BYTES+1; HEAD=32
ARRAY_HEADER=sys.getsizeof(np.empty(0,np.uint8))


def layout(budget_bytes,prefix_bits=40,ways=4):
    assert ways==4 and int(budget_bytes)==budget_bytes and budget_bytes>=0
    nb=max(0,(int(budget_bytes)-ARRAY_HEADER-HEAD)//BUCKET_BYTES)
    size=ARRAY_HEADER+HEAD+nb*BUCKET_BYTES if nb else 0
    return dict(buckets=nb,slots=4*nb,allocated_bytes=size,budget_bytes=int(budget_bytes),nbytes=size-ARRAY_HEADER if nb else 0)


def allocate(spec):
    data=np.zeros(spec['nbytes'],np.uint8)
    if spec['buckets']:
        data[:8]=np.frombuffer(b'EXACT041',dtype=np.uint8)
        data[8:16]=np.frombuffer(int(spec['buckets']).to_bytes(8,'little'),dtype=np.uint8)
        assert sys.getsizeof(data)==spec['allocated_bytes']<=spec['budget_bytes'] and data.flags.owndata
    return data


@njit(cache=True)
def bucket(h,nb):
    return np.int64(((np.uint64(h)>>np.uint64(32))*np.uint64(nb))>>np.uint64(32))


@njit(cache=True)
def lookup(data,h,key,nb):
    if nb==0 or len(key)>KEY_BYTES:return False
    start=HEAD+bucket(h,nb)*BUCKET_BYTES
    for w in range(4):
        p=start+w*SLOT_BYTES
        if data[p+130]==0:continue
        n=np.int64(data[p+128])+256*np.int64(data[p+129])
        if n!=len(key):continue
        equal=True
        for j in range(n):
            if data[p+j]!=key[j]:equal=False;break
        if equal:data[p+131]=1;return True
    return False


@njit(cache=True)
def insert(data,h,key,nb):
    if nb==0 or len(key)>KEY_BYTES:return 0
    start=HEAD+bucket(h,nb)*BUCKET_BYTES; chosen=-1
    for w in range(4):
        if data[start+w*SLOT_BYTES+130]==0:chosen=w;break
    evicted=chosen<0
    if evicted:
        hand=np.int64(data[start+4*SLOT_BYTES])
        for _ in range(8):
            p=start+hand*SLOT_BYTES
            if data[p+131]==0:chosen=hand;break
            data[p+131]=0;hand=(hand+1)%4
        if chosen<0:chosen=hand
        data[start+4*SLOT_BYTES]=(chosen+1)%4
    p=start+chosen*SLOT_BYTES
    for j in range(KEY_BYTES):data[p+j]=key[j] if j<len(key) else 0
    data[p+128]=len(key)%256;data[p+129]=len(key)//256;data[p+130]=1;data[p+131]=1
    return 2 if evicted else 1


@njit(cache=True)
def replay(stream,hashes,blob,offsets,flags,member,data,nb):
    # Actual labels used only in this offline reference, not a deployment query path.
    cnt=np.zeros(8,np.int64) # calls, FP, found, cachehits, FN, insert, eviction, bypass
    for ix in stream:
        x=np.int64(ix);key=blob[offsets[x]:offsets[x+1]]
        if lookup(data,hashes[x],key,nb):cnt[3]+=1;cnt[4]+=np.int64(member[x])
        elif flags[x]:
            cnt[0]+=1
            if member[x]:cnt[2]+=1
            else:
                cnt[1]+=1;action=insert(data,hashes[x],key,nb)
                cnt[5]+=np.int64(action>0);cnt[6]+=np.int64(action==2);cnt[7]+=np.int64(action==0)
        else:cnt[4]+=np.int64(member[x])
    return cnt


@njit(cache=True)
def member_hits(data,hashes,blob,offsets,indices,nb):
    hits=0
    for x in indices:
        if lookup(data,hashes[x],blob[offsets[x]:offsets[x+1]],nb):hits+=1
    return hits


def pack(keys):
    offsets=np.zeros(len(keys)+1,np.int64)
    offsets[1:]=np.cumsum([len(k) for k in keys])
    return np.frombuffer(b''.join(keys),np.uint8).copy(),offsets


@contextmanager
def exact_layout():
    assert E5.K is K,'Unexpected preexisting allocator binding'
    E5.K=sys.modules[__name__]
    try:yield
    finally:E5.K=K


def evaluate(c,stream,s,blob,offsets):
    spec=layout(c['cache_bytes']);data=allocate(spec)
    cnt=replay(stream,s.h1q,blob,offsets,c['structure'].fp_static,np.zeros(len(s.h1q),np.bool_),data,spec['buckets'])
    assert cnt[4]==0 and cnt[0]==cnt[1]
    return int(cnt[1]),data,cnt


def replay_best(cands,stream,s,blob,offsets):
    best=None
    for c in sorted(cands,key=lambda c:c['structure'].est_fpr):
        fp,_,_=evaluate(c,stream,s,blob,offsets)
        key=(fp,c['structure'].est_fpr,c['trees'],c['frac'])
        if best is None or key<best[0]:best=(key,c)
    assert best is not None
    return best[1],best[0][0]

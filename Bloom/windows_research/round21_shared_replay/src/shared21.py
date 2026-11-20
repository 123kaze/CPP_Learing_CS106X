"""Exact event-routed joint CLOCK replay; no estimator or decision-rule change.

A non-FP request may hit a verified prefix and change CLOCK reference bits.
Routes therefore cover static positives AND the union of all prefixes that an
observed static-positive key could insert, clipped to that candidate's bucket.
fp64 routes cover full-fingerprint aliases too. Only impossible state-changing
requests are skipped. Candidate state and eight counters match complete replay.
"""
import os
for n in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[n]='1'
from pathlib import Path
import sys
import time
import numpy as np
from numba import njit
from numba.typed import List
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round20_zero_guard/src'))
import guard20 as G
E5=G.E5;C5=G.BF.CACHES['index'];F64=G.BF.CACHES['fp64']


@njit(cache=True)
def mark_intervals(sorted_h,order,lower,upper,route_word,bit):
    """Union intervals sorted by lower endpoint, swept against observed hashes."""
    j=0;active=False;end=np.uint64(0)
    for p in range(len(sorted_h)):
        h=sorted_h[p]
        while j<len(lower) and lower[j]<=h:
            if not active or upper[j]>end:end=upper[j]
            active=True;j+=1
        if active and h<=end:route_word[order[p]]|=bit


@njit(cache=True)
def bit_index(mask):
    """Index of lowest set bit; no Python object iteration or floating conversion."""
    n=0
    if mask&np.uint64(0xffffffff)==0:mask>>=np.uint64(32);n+=32
    if mask&np.uint64(0xffff)==0:mask>>=np.uint64(16);n+=16
    if mask&np.uint64(0xff)==0:mask>>=np.uint64(8);n+=8
    if mask&np.uint64(0xf)==0:mask>>=np.uint64(4);n+=4
    if mask&np.uint64(0x3)==0:mask>>=np.uint64(2);n+=2
    if mask&np.uint64(1)==0:n+=1
    return n


@njit(cache=True)
def joint_loop(stream,local,hashes,safe,accept,route,states,layout,counters,fp64):
    visits=np.zeros(len(states),np.int64)
    for pos in range(len(stream)):
        index=np.int64(stream[pos])
        assert 0<=index<len(local), 'Stream index outside pool'
        x=np.int64(local[index])
        assert x>=0, 'Stream contains a key absent from supplied statistics'
        h=hashes[x]
        for word in range(route.shape[0]):
            mask=route[word,x]
            while mask:
                offset=bit_index(mask);j=word*64+offset
                mask&=mask-np.uint64(1)
                visits[j]+=1
                B,Q,ob,sb,hb=layout[j]
                hit=(F64.lookup(states[j],h,B,64,Q,ob,sb,4) if fp64 else C5.lookup(states[j],h,B,40,Q,ob,sb,4))
                if hit:counters[j,1]+=1
                elif accept[word,x]&(np.uint64(1)<<np.uint64(offset)):
                    counters[j,0]+=1
                    outcome=(F64.insert(states[j],h,B,64,Q,ob,sb,4,hb) if fp64 else C5.insert(states[j],h,safe[x],B,40,Q,ob,sb,4,hb))
                    if outcome:
                        counters[j,2]+=1
                        if outcome==2:counters[j,3]+=1
                        else:counters[j,7]+=1
                    else:counters[j,4]+=1
    for j in range(len(states)):counters[j,5]=len(stream)
    return visits


def prepare(candidates,hashes,safe,keys,counts,mode):
    if mode not in ('index','fp64'):raise ValueError('Unknown cache format')
    if not candidates:raise ValueError('At least one candidate required')
    if len(keys)>2**31-1:raise ValueError('Local key map exceeds int32')
    assert len(keys)==len(counts) and counts.sum()>0
    assert np.all(keys>=0) and np.all(keys<len(hashes))
    assert np.all(np.diff(keys)>0)
    fp64=mode=='fp64';cache=F64 if fp64 else C5
    if not fp64:
        assert safe is not None and len(safe)==len(hashes)
        assert np.all(safe[keys]>=1)
    h=np.ascontiguousarray(hashes[keys],dtype=np.uint64)
    safe_local=np.zeros(len(keys),np.uint8) if fp64 else np.ascontiguousarray(safe[keys])
    order=np.argsort(h,kind='stable');sorted_h=h[order]
    local=np.full(len(hashes),-1,np.int32);local[keys]=np.arange(len(keys),dtype=np.int32)
    words=(len(candidates)+63)//64
    accept=np.zeros((words,len(keys)),np.uint64);route=np.zeros_like(accept)
    layout=np.zeros((len(candidates),5),np.int64);counters=np.zeros((len(candidates),8),np.int64)
    states=List();additional=[]
    for j,c in enumerate(candidates):
        sp=cache.layout(c['cache_bytes']);state=cache.allocate(sp);states.append(state)
        layout[j]=sp['buckets'],sp['Q'],sp['ob'],sp['slot_bits'],sp['handbits']
        flags=np.asarray(c['structure'].fp_static[keys],np.bool_)
        word=j//64;bit=np.uint64(1)<<np.uint64(j%64)
        accept[word,flags]|=bit
        if not sp['buckets']:
            # Exact no-cache shortcut; match frozen replay's bypass/processed counts.
            fp=int(counts[flags].sum());counters[j,0]=fp;counters[j,4]=0 if fp64 else fp;counters[j,5]=int(counts.sum())
            additional.append(0);continue
        route[word,flags]|=bit
        eligible=flags if fp64 else flags&(safe_local<=40)
        inserted=h[eligible]
        if len(inserted):
            if fp64:lower=inserted;upper=inserted
            else:
                lengths=safe_local[eligible].astype(np.uint64)
                suffix=(np.uint64(1)<<(np.uint64(64)-lengths))-np.uint64(1)
                lower=inserted&~suffix;upper=lower|suffix
                # lookup only visits the quotient bucket assigned to this hash.
                B=np.uint64(sp['buckets'])
                bucket=((inserted>>np.uint64(32))*B)>>np.uint64(32)
                start=((bucket<<np.uint64(32))+B-np.uint64(1))//B
                last=(((bucket+np.uint64(1))<<np.uint64(32))+B-np.uint64(1))//B-np.uint64(1)
                lower=np.maximum(lower,start<<np.uint64(32))
                upper=np.minimum(upper,(last<<np.uint64(32))|np.uint64(0xffffffff))
            idx=np.argsort(lower,kind='stable')
            mark_intervals(sorted_h,order,np.ascontiguousarray(lower[idx]),np.ascontiguousarray(upper[idx]),route[word],bit)
        additional.append(int(((route[word]&bit)!=0).sum()-flags.sum()))
    return dict(local=local,hashes=h,safe=safe_local,accept=accept,route=route,states=states,layout=layout,counters=counters,
                fp64=fp64,additional_routed_keys=additional,
                route_workspace_payload_bytes=sum(a.nbytes for a in (local,h,safe_local,accept,route,layout,counters)),
                cache_state_bytes=sum(s.nbytes for s in states))


def replay(candidates,learn,setup,safe,keys,counts,mode):
    """Counts are supplied by the already measured common learning summarizer.

    Includes local-map/mask preparation and cache allocation. Only cache simulation
    is a single ordered traversal; this is not a claim of one total input read.
    """
    start=time.perf_counter()
    assert len(learn)==int(counts.sum()), 'Supplied frequencies disagree with stream length'
    p=prepare(candidates,setup.h1q,safe,keys,counts,mode)
    prepared=time.perf_counter()
    visits=joint_loop(learn,p['local'],p['hashes'],p['safe'],p['accept'],p['route'],p['states'],p['layout'],p['counters'],p['fp64'])
    end=time.perf_counter()
    p.update(elapsed_s=end-start,route_prepare_s=prepared-start,ordered_scan_s=end-prepared,visits=visits)
    return p


def gate_choice(candidates,counts):
    """First13 candidates are BF fractions; final candidate is the RA6 anchor."""
    if len(candidates)!=14 or any(c['trees']!=0 for c in candidates[:13]) or candidates[-1]['trees']==0:
        raise ValueError('Expected13 BF candidates and one learned anchor')
    winner=min(range(13),key=lambda j:(int(counts[j,0]),candidates[j]['structure'].est_fpr,0,candidates[j]['frac']))
    selected=winner if counts[winner,0]<=counts[13,0] else 13
    return selected,winner


def serial_full(candidates,learn,setup,safe,mode):
    cache=F64 if mode=='fp64' else C5
    states=[];counters=[]
    for c in candidates:
        sp=cache.layout(c['cache_bytes']);state=cache.allocate(sp)
        if mode=='fp64':
            count=F64.replay(learn,setup.h1q,np.zeros(0,np.bool_),c['structure'].fp_static,state,sp['buckets'],64,sp['Q'],sp['ob'],sp['slot_bits'],4,sp['handbits'],2**62,np.zeros(0,np.int64),np.zeros(0,np.bool_))[:8]
        else:
            count=C5.replay(learn,setup.h1q,safe,c['structure'].fp_static,state,sp['buckets'],40,sp['Q'],sp['ob'],sp['slot_bits'],4,sp['handbits'],2**62,np.zeros(0,np.int64),np.zeros(0,np.bool_))
        states.append(state);counters.append(count)
    return np.stack(counters),states

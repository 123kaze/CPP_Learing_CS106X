"""Scalar probes and actual-SQL feedback; online driver has no membership labels."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
for r in ('round5_dp','round6_bucket','round12_nomodel','round19_gt_fix'):sys.path.insert(0,str(WR/r/'src'))
import engine5 as E5
import e789 as J
import baseline as B
import numpy as np
from numba import njit
import time
import json
import hashlib
K=E5.K


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');q.replace(p)


@njit(cache=True)
def probe_learned(x,X,hashes,feat,thr,left,right,leaf,roots,region_cuts,kind,off,m,k,bits,data,nb,Q,ob,sb):
    h=hashes[x]
    if nb and K.lookup(data,h,nb,40,Q,ob,sb,4):return 2
    score=0.
    for root in roots:
        n=np.int64(root)
        while n>=0:n=np.int64(left[n] if X[x,feat[n]]<=thr[n] else right[n])
        score+=leaf[~n]
    g=np.searchsorted(region_cuts,score,side='left')
    if kind[g]==J.PASS:return 1
    if kind[g]!=J.BF:return 0
    for j in range(k[g]):
        p=off[g]+E5.C.bf_pos(h,j,m[g])
        if (bits[p>>3]>>np.uint64(p&7))&np.uint64(1)==0:return 0
    return 1


@njit(cache=True)
def probe_bf(x,hashes,bf,data,nb,Q,ob,sb):
    h=hashes[x]
    if nb and K.lookup(data,h,nb,40,Q,ob,sb,4):return 2
    m,k=np.int64(bf[1]),np.int64(bf[2])
    for j in range(k):
        p=E5.C.bf_pos(h,j,m)
        if (bf[B.HEAD_WORDS+(p>>6)]>>np.uint64(p&63))&np.uint64(1)==0:return 0
    return 1


@njit(cache=True)
def feedback_absent(h,sorted_members,data,nb,Q,ob,sb,hb):
    if not nb:return 0
    return K.insert(data,h,J.safe_len(sorted_members,h),nb,40,Q,ob,sb,4,hb)


@njit(cache=True)
def many_learned(indices,args):
    out=np.empty(len(indices),np.uint8)
    for i,x in enumerate(indices):out[i]=probe_learned(x,*args)
    return out


@njit(cache=True)
def many_bf(indices,args):
    out=np.empty(len(indices),np.uint8)
    for i,x in enumerate(indices):out[i]=probe_bf(x,*args)
    return out


@njit(cache=True)
def reference_bf(stream,hashes,member,bf,data,sorted_members,nb,Q,ob,sb,hb):
    """Label-based reference only. Never used in the timed online driver."""
    acc=np.zeros(len(stream),np.uint8);counts=np.zeros(4,np.int64)
    for i,x in enumerate(stream):
        outcome=probe_bf(x,hashes,bf,data,nb,Q,ob,sb)
        if outcome==2:counts[3]+=1
        elif outcome==1:
            acc[i]=1;counts[0]+=1
            if member[x]:counts[2]+=1
            else:
                counts[1]+=1;feedback_absent(hashes[x],sorted_members,data,nb,Q,ob,sb,hb)
    return counts,acc


class Online:
    def __init__(self,c,space,learned=None):
        self.c=c;self.hashes=space.h;self.sorted_members=space.sorted_m;self.is_learned=learned is not None
        self.spec=K.layout(c['cache_bytes']);self.X=space.X if self.is_learned else None
        # No space/member labels or legacy Exe object are retained in the online adapter.
        # Only4 region cuts are used online; expanded lookup buffers are reference-only.
        self.region_cuts=learned.raw_cuts[c['structure'].b[1:-1]].copy() if self.is_learned else None
        if self.is_learned:
            x=learned;self.impl=probe_learned
            self.base_args=(self.X,self.hashes,*x.model,self.region_cuts,c['structure'].kind,x.off,x.m,x.k,x.bits)
        else:
            self.impl=probe_bf;self.base_args=(self.hashes,c['structure'].data)
        self.reset()

    def reset(self):
        self.data=np.zeros(1,np.uint64) if self.is_learned and not self.spec['buckets'] else K.allocate(self.spec)
        p=self.spec;cache=(self.data,p['buckets'],p['Q'],p['ob'],p['slot_bits'])
        self.args=(*self.base_args,*cache)
        self.feedback_args=(self.sorted_members,*cache,p['handbits'])

    def probe(self,x):return self.impl(x,*self.args)
    def absent(self,x):return feedback_absent(self.hashes[x],*self.feedback_args)
    def all_probes(self,indices):return (many_learned if self.is_learned else many_bf)(indices,self.args)


def online_run(cursor,query,keys,requests,flt,accepted):
    """Timer encloses real per-request interleaving. No labels/ground-truth argument."""
    calls=misses=found=hits=rejects=inserts=evictions=bypasses=0
    probe=flt.probe if flt is not None else None
    absent=flt.absent if flt is not None else None
    t0=time.perf_counter_ns()
    for i,index in enumerate(requests):
        x=int(index);decision=probe(x) if probe is not None else 1
        if decision==2:hits+=1;continue
        if decision==0:rejects+=1;continue
        accepted[i]=1;calls+=1
        row=cursor.execute(query,(int(keys[x]),)).fetchone()
        if row is not None:found+=1
        else:
            misses+=1
            # This is the ONLY admission site in the online driver.
            if absent is not None:
                action=absent(x)
                if action:inserts+=1;evictions+=int(action==2)
                else:bypasses+=1
    elapsed=time.perf_counter_ns()-t0
    return dict(elapsed_ns=elapsed,ns_per_query=elapsed/len(requests),backend_calls=calls,fp=misses,members_found=found,cache_hits=hits,
                filter_rejects=rejects,inserts=inserts,evictions=evictions,bypasses=bypasses)

"""Fixed-region allocation and explicitly external-T cache mechanics."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
for r in ('round5_dp','round12_nomodel','round22_kl_diagnostic_v2'):
    sys.path.insert(0,str(WR/r/'src'))
import engine5 as E5
import baseline as B
from math22 import capped
import numpy as np
from numba import njit
A=np.log(2)**2


def masses(prob,region,T,H,k):
    assert T>=0 and H>0 and np.all((prob>=0)&(prob<=1))
    with np.errstate(divide='ignore'):
        log_survival=np.log1p(-prob)
    upto=min(T,H)
    exact=H*prob if T==0 else -np.expm1(upto*log_survival)+max(0,H-T)*prob*np.exp(T*log_survival)
    first=-np.expm1(-prob*H)
    che=first+(prob*H-first)*np.exp(-prob*T)
    assert np.all(exact>=0) and np.all(che>=0)
    return (np.bincount(region,weights=che,minlength=k),np.bincount(region,weights=exact,minlength=k),che,exact)


def identity(n,h,M,bits):
    n,h,M=map(lambda x:np.asarray(x,float),(n,h,M));p=n/n.sum()
    eh,em=capped(n,h,bits),capped(n,M,bits)
    active=p>0
    supports=bool(np.all(h[active]>0) and np.all(M[active]>0))
    factor=None
    if supports:
        rho=M[active]/h[active];factor=float(p[active]@rho*np.exp(-p[active]@np.log(rho)))
    interior=bool(supports and np.all(eh[active]<1-1e-10) and np.all(em[active]<1-1e-10))
    baseline=float(M@eh);optimal=float(M@em)
    assert optimal<=baseline+max(1e-7,baseline*1e-10)
    if interior:assert np.isclose(baseline/optimal,factor,rtol=1e-9,atol=1e-10)
    return dict(h=h.tolist(),M=M.tolist(),p=p.tolist(),rho=[float(M[i]/h[i]) if h[i]>0 else None for i in range(len(n))],
                baseline_epsilon=eh.tolist(),reweighted_epsilon=em.tolist(),interior=interior,
                arithmetic_geometric_factor=factor,predicted_gain=1-1/factor if factor else None,
                conditional_baseline_fp=baseline,conditional_reweighted_fp=optimal,conditional_gain=1-optimal/baseline if baseline else None)


def probabilities(region,h,amplitude):
    """Same regional query masses; change only within-region concentration."""
    k=len(h);prob=np.zeros(len(region));rng=np.random.default_rng(2800)
    actual=np.array([h[i] if np.any(region==i) else 0. for i in range(k)]);actual/=actual.sum()
    exponents=1+.6*amplitude*np.linspace(-1,1,k)
    for i in range(k):
        keys=np.flatnonzero(region==i);rng.shuffle(keys)
        if not len(keys):continue
        w=np.arange(1,len(keys)+1,dtype=float)**(-exponents[i]);prob[keys]=actual[i]*w/w.sum()
    assert np.isclose(prob.sum(),1.)
    assert np.allclose(np.bincount(region,weights=prob,minlength=k),actual)
    return prob,actual,exponents


@njit(cache=True)
def ttl_misses(stream,nkeys,T):
    """Per-key miss counts of renewing TTL; independent of other keys' admission."""
    last=np.full(nkeys,-T-2,np.int64);counts=np.zeros(nkeys,np.int64)
    for i in range(len(stream)):
        q=np.int64(stream[i])
        if i-last[q]>T:counts[q]+=1
        last[q]=i
    return counts


def physical(n,eps,member_hashes,negative_hashes,member_region,negative_region,budget_bits):
    m=np.floor(n*(-np.log(np.maximum(eps,1e-300)))/A).astype(np.int64)
    m[n==0]=0
    assert m.sum()<=budget_bits+1e-6
    kind=np.where(n==0,E5.C.EMPTY,np.where(m>0,E5.C.BF,E5.C.PASS)).astype(np.uint8)
    kval=np.array([B.optimal_k(int(ni),int(mi)) if ni>0 and mi>0 else 0 for ni,mi in zip(n,m)],np.int64)
    off=np.concatenate([[0],np.cumsum(m)]).astype(np.int64);bits=np.zeros((int(off[-1])+7)//8,np.uint8)
    E5.R.packed_build(member_hashes,member_region,off,m,kval,bits)
    assert E5.R.packed_query(member_hashes,member_region,kind,off,m,kval,bits).all()
    flags=E5.R.packed_query(negative_hashes,negative_region,kind,off,m,kval,bits)
    integer=np.zeros(len(n));pos=n>0;integer[pos]=1.;b=(n>0)&(m>0)
    integer[b]=(-np.expm1(-kval[b]*n[b]/m[b]))**kval[b]
    meta=dict(region_bits=m.tolist(),region_hash_probes=kval.tolist(),payload_bytes=bits.nbytes,used_bits=int(m.sum()),unused_budget_bits=int(budget_bits-m.sum()),
              navigation_payload_bytes=sum(v.nbytes for v in (kind,m,kval,off)),array_header_bytes=sum(sys.getsizeof(v)-v.nbytes for v in (kind,m,kval,off,bits)),
              integer_fpr=integer.tolist(),member_fn=0)
    return flags,meta


def clock(stream,hashes,safe,flags,member_hashes,cache_bytes=2048):
    K=E5.K;spec=K.layout(cache_bytes);data=K.allocate(spec)
    cnt=K.replay(stream,hashes,safe,flags,data,spec['buckets'],40,spec['Q'],spec['ob'],spec['slot_bits'],4,spec['handbits'],2**62,np.empty(0,np.int64),np.empty(0,np.bool_))
    assert cnt[5]==len(stream) and cnt[6]==0
    assert K.count_member_hits(data,member_hashes,spec['buckets'],40,spec['Q'],spec['ob'],spec['slot_bits'],4)==0
    return dict(zip(('fp','hits','inserts','evictions','bypasses','processed','cutoff','occupied'),map(int,cnt))),spec['allocated_bytes']

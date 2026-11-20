"""Physically accounted static PLBF with replaceable scorers; no negative cache."""
import math
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from numba import njit
from scipy.special import expit
from models23 import score_one,arguments
WR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WR/'round12_nomodel/src'))
import baseline as B
E5=B.E5;D=E5.D;C=E5.C;R=E5.R


def build(meta,model,raw,y,split,hashes,kib):
    seg=D.segment_of(expit(raw))
    td=SimpleNamespace(g=np.bincount(seg[y],minlength=D.N_SEG),v=np.bincount(seg[split['neg_val']],minlength=D.N_SEG))
    # Explicit24B dispatch/layout header is deployed; otherwise only actual owning arrays.
    header=np.array([2301,meta['code'],meta['features'],16,8,D.K_REG],np.int32)
    dummy=[np.empty(4,np.float64),np.empty(5,np.uint8),np.empty(6,np.int64),np.empty(5,np.int64),np.empty(5,np.int64),np.empty(0,np.uint8)]
    model_bytes=sum(sys.getsizeof(a) for a in model.values())
    fixed=model_bytes+sys.getsizeof(header)+sum(sys.getsizeof(a) for a in dummy)
    avail=(kib*1024-fixed)*8
    if avail<=0:raise ValueError('Model and metadata leave no BF capacity')
    M=float(avail)
    for _ in range(20):
        bounds,f,_=D.allocate(td.g,td.v+1.,M)
        reg,n,bpm,m,kind=E5.region_bits(td,bounds,f)
        if m.sum()<=avail:break
        M*=avail/m.sum()*.9999
    assert m.sum()<=avail
    k=np.where(kind==C.BF,np.maximum(1,np.rint(bpm*np.log(2))),0).astype(np.int64)
    off=np.concatenate([[0],np.cumsum(m)]).astype(np.int64)
    bits=np.zeros((int(off[-1])+7)//8,np.uint8)
    # Store probability-space cuts; exact same segment boundary semantics at saturation.
    cuts=(bounds[1:-1]/D.N_SEG).copy()
    R.packed_build(hashes[y],reg[seg[y]].astype(np.int32),off,m,k,bits)
    allflags=R.packed_query(hashes,reg[seg].astype(np.int32),kind,off,m,k,bits)
    assert allflags[y].all()
    layout=dict(header=header,cuts=cuts,kind=kind.copy(),off=off,m=m.copy(),k=k.copy(),bits=bits)
    used=model_bytes+sum(sys.getsizeof(a) for a in layout.values())
    assert used<=kib*1024 and all(a.flags.owndata for a in list(model.values())+list(layout.values()))
    return layout,allflags,dict(total_bytes=used,model_bytes_with_headers=model_bytes,
            model_payload_bytes=sum(a.nbytes for a in model.values()),filter_payload_bytes=bits.nbytes,
            metadata_and_headers_bytes=used-model_bytes-bits.nbytes,budget_kib=kib)


@njit(cache=True)
def prob(s):
    if s>=0:return 1/(1+math.exp(-s))
    e=math.exp(s);return e/(1+e)


@njit(cache=True)
def query_kernel(X,hashes,idx,code,d,params,edges,feat,thr,left,right,leaf,roots,cuts,kind,off,m,k,bits):
    flags=np.empty(len(idx),np.bool_)
    for j in range(len(idx)):
        i=idx[j];s=score_one(X[i],code,d,params,edges,feat,thr,left,right,leaf,roots)
        region=np.searchsorted(cuts,prob(s),side='left')
        yes=kind[region]==C.PASS
        if kind[region]==C.BF:
            yes=True
            for probe in range(k[region]):
                p=off[region]+C.bf_pos(hashes[i],probe,m[region])
                if (bits[p>>3]>>np.uint8(p&7))&np.uint8(1)==0:yes=False;break
        flags[j]=yes
    return flags


def query(X,hashes,idx,meta,model,layout):
    return query_kernel(X,hashes,idx,*arguments(meta,model),*(layout[k] for k in ('cuts','kind','off','m','k','bits')))


@njit(cache=True)
def bf_query(data,hashes,idx):
    flags=np.ones(len(idx),np.bool_);m,k=np.int64(data[1]),np.int64(data[2])
    for i in range(len(idx)):
        h=hashes[idx[i]]
        for j in range(k):
            p=C.bf_pos(h,j,m)
            if (data[4+(p>>6)]>>np.uint64(p&63))&np.uint64(1)==0:flags[i]=False;break
    return flags

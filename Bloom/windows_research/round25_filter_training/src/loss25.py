"""Capped static BF surrogate with soft ordered regions and envelope gradients.

No cache, latent future labels, raw unclipped-KL loss or new model capacity.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import sys
import numpy as np
from scipy.special import expit
from scipy.optimize import brentq
WR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WR/'round23_lightweight/src'))
import models23 as M
A=np.log(2)**2


def capped(p,q,beta):
    p=np.asarray(p,np.float64);q=np.asarray(q,np.float64)
    if beta<=0 or np.any(p<=0) or np.any(q<=0):raise ValueError('Strictly positive soft histograms and bit budget required')
    z=np.log(q/p)
    hi=float(z.max()+1);lo=float(z.min()-beta/p.sum()-2)
    logc=brentq(lambda u:float(p@np.maximum(z-u,0))-beta,lo,hi,xtol=1e-13)
    bits=np.maximum(z-logc,0);epsilon=np.exp(-bits);J=float(q@epsilon)
    assert np.isclose(p@bits,beta,rtol=1e-9,atol=1e-10)
    return J,epsilon,float(np.exp(logc)),bits


def soft_regions(scores,cuts,tau):
    cdf=expit((cuts[None,:]-scores[:,None])/tau)
    d=-cdf*(1-cdf)/tau
    bins=np.column_stack([cdf[:,0],np.diff(cdf,axis=1),1-cdf[:,-1]])
    derivative=np.column_stack([d[:,0],np.diff(d,axis=1),-d[:,-1]])
    return bins,derivative


def forward(w,Z):
    d=Z.shape[1];end=d*8
    W=w[:end].reshape(d,8);b=w[end:end+8];v=w[end+8:end+16]
    hidden=np.maximum(Z@W+b,0)
    return hidden@v+w[-1],hidden,W,v


def surrogate_scores(scores,y,cuts,tau,beta):
    assignment,derivative=soft_regions(scores,cuts,tau)
    pos=y.astype(bool);n0=int((~pos).sum());n1=int(pos.sum());regions=assignment.shape[1]
    if n0==0 or n1==0:raise ValueError('Both classes required')
    # Fixed one pseudo-count per region avoids log0; not fitted from test data.
    p=(assignment[pos].sum(axis=0)+1)/(n1+regions)
    q=(assignment[~pos].sum(axis=0)+1)/(n0+regions)
    J,eps,mult,used=capped(p,q,beta)
    influence=np.empty_like(assignment)
    influence[pos]=mult*used/(J*(n1+regions))
    influence[~pos]=eps/(J*(n0+regions))
    ds=np.sum(influence*derivative,axis=1)
    return float(np.log(J)),ds,dict(p=p,q=q,J=J,epsilon=eps,log_inverse_FPR=used,
                                   active_regions=int(np.sum(used>1e-10)),member_weighted_log_bits=float(p@used))


def objective(w,Z,y,cuts,tau,beta):
    scores,hidden,W,v=forward(w,Z)
    value,err,_=surrogate_scores(scores,y,cuts,tau,beta)
    back=err[:,None]*v*(hidden>0)
    regularizer=.5*M.L2*(np.sum(W*W)+np.dot(v,v))
    gradient=np.concatenate([(Z.T@back+M.L2*W).ravel(),back.sum(axis=0),hidden.T@err+M.L2*v,[err.sum()]])
    return value+float(regularizer),gradient

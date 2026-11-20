"""Small scoring models, conventional training only. Preprocessing is train-only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import math
import sys
from pathlib import Path
import numpy as np
from scipy.special import expit
from scipy.optimize import minimize
from numba import njit
WR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WR/'src'))
from end_to_end import model_arrays
MODELS=('LR','GaussianNB','Additive16','MLP8','Tree1','Tree16')
CODE={'LR':1,'GaussianNB':2,'Additive16':3,'MLP8':4,'Tree1':5,'Tree16':5}
L2=1e-4;MAXITER=100;HIDDEN=8;BINS=16
# Dummy dispatch arrays are shared harness inputs, not serialized model parameters.
EMPTY16=np.empty(0,np.int16);EMPTY64=np.empty(0,np.float64)


def preprocess(X):
    mean=X.mean(axis=0,dtype=np.float64);std=X.std(axis=0,dtype=np.float64)
    std=np.where(std>1e-12,std,1.)
    return mean,std


def bin_matrix(X,edges):
    return np.column_stack([np.searchsorted(edges[j],X[:,j],side='right') for j in range(X.shape[1])]).astype(np.int64)


def linear_objective(w,Z,y):
    score=Z@w[:-1]+w[-1];err=expit(score)-y
    loss=np.logaddexp(0,score).mean()-np.dot(y,score)/len(y)+.5*L2*np.dot(w[:-1],w[:-1])
    gradient=np.concatenate([Z.T@err/len(y)+L2*w[:-1],[err.mean()]])
    return float(loss),gradient


def additive_objective(w,bins,y):
    d=bins.shape[1];offset=np.arange(d)*BINS
    codes=bins+offset
    score=w[codes].sum(axis=1)+w[-1];err=expit(score)-y
    loss=np.logaddexp(0,score).mean()-np.dot(y,score)/len(y)+.5*L2*np.dot(w[:-1],w[:-1])
    g=np.empty_like(w)
    for j in range(d):g[j*BINS:(j+1)*BINS]=np.bincount(bins[:,j],weights=err,minlength=BINS)/len(y)
    g[:-1]+=L2*w[:-1];g[-1]=err.mean()
    return float(loss),g


def mlp_objective(w,Z,y):
    d=Z.shape[1];h=HIDDEN;end=d*h
    W=w[:end].reshape(d,h);bias=w[end:end+h];v=w[end+h:end+2*h]
    hidden=np.maximum(Z@W+bias,0);score=hidden@v+w[-1];err=(expit(score)-y)/len(y)
    loss=np.logaddexp(0,score).mean()-np.dot(y,score)/len(y)+.5*L2*(np.sum(W*W)+np.dot(v,v))
    back=err[:,None]*v*(hidden>0)
    grad=np.concatenate([(Z.T@back+L2*W).ravel(),back.sum(axis=0),hidden.T@err+L2*v,[err.sum()]])
    return float(loss),grad


def fit(name,X,y,seed):
    X=np.asarray(X,np.float64);y=np.asarray(y,np.float64);d=X.shape[1]
    assert np.isfinite(X).all() and 0<y.sum()<len(y)
    meta=dict(name=name,code=CODE[name],features=d,seed=seed)
    if name.startswith('Tree'):
        import lightgbm as lgb
        trees=int(name[4:])
        m=lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,
                         deterministic=True,force_col_wise=True,verbose=-1),lgb.Dataset(X,label=y),num_boost_round=trees)
        arrays=model_arrays(m)
        meta.update(optimizer='LightGBM binary objective',trees=trees,fit_status='completed')
        reference=lambda A:m.predict(A,raw_score=True,num_threads=1)
        return meta,arrays,reference
    if name=='Additive16':
        edges=np.quantile(X,np.arange(1,BINS)/BINS,axis=0).T.copy()
        bins=bin_matrix(X,edges)
        w=np.zeros(d*BINS+1);w[-1]=math.log(y.mean()/(1-y.mean()))
        res=minimize(additive_objective,w,args=(bins,y),jac=True,method='L-BFGS-B',options=dict(maxiter=MAXITER,ftol=1e-10,gtol=1e-6))
        arrays={'params':res.x.copy(),'edges':edges.ravel().copy()}
        reference=lambda A:res.x[bin_matrix(A,edges)+np.arange(d)*BINS].sum(axis=1)+res.x[-1]
    else:
        mean,std=preprocess(X);Z=np.ascontiguousarray((X-mean)/std)
        if name=='GaussianNB':
            mu=np.stack([Z[y==c].mean(axis=0) for c in (0,1)])
            var=np.stack([Z[y==c].var(axis=0) for c in (0,1)])+1e-6
            prior=math.log(y.mean()/(1-y.mean()))
            params=np.concatenate([mean,std,mu.ravel(),var.ravel(),[prior]])
            arrays={'params':params}
            def reference(A):
                zz=(A-mean)/std
                return prior-.5*(np.log(var[1]/var[0])+(zz-mu[1])**2/var[1]-(zz-mu[0])**2/var[0]).sum(axis=1)
            meta.update(optimizer='Closed-form GaussianNB, train-derived scale; variance floor1e-6',fit_status='completed')
            return meta,arrays,reference
        if name=='LR':
            w=np.zeros(d+1);w[-1]=math.log(y.mean()/(1-y.mean()))
            res=minimize(linear_objective,w,args=(Z,y),jac=True,method='L-BFGS-B',options=dict(maxiter=MAXITER,ftol=1e-10,gtol=1e-6))
            reference=lambda A:((A-mean)/std)@res.x[:-1]+res.x[-1]
        elif name=='MLP8':
            rng=np.random.default_rng(seed);W=rng.normal(0,1/math.sqrt(d),(d,HIDDEN));v=rng.normal(0,1/math.sqrt(HIDDEN),HIDDEN)
            w=np.concatenate([W.ravel(),np.zeros(HIDDEN),v,[math.log(y.mean()/(1-y.mean()))]])
            res=minimize(mlp_objective,w,args=(Z,y),jac=True,method='L-BFGS-B',options=dict(maxiter=MAXITER,ftol=1e-10,gtol=1e-6))
            reference=lambda A:np.maximum(((A-mean)/std)@res.x[:d*HIDDEN].reshape(d,HIDDEN)+res.x[d*HIDDEN:d*HIDDEN+HIDDEN],0)@res.x[d*HIDDEN+HIDDEN:-1]+res.x[-1]
        else:raise ValueError(name)
        arrays={'params':np.concatenate([mean,std,res.x])}
    if not np.isfinite(res.fun) or not np.isfinite(res.x).all():raise ValueError('Nonfinite optimization')
    # A fixed training budget may end before convergence. Preserve status; do not retry to improve a result.
    meta.update(optimizer='L-BFGS-B',optimizer_success=bool(res.success),optimizer_status=int(res.status),
                optimizer_message=str(res.message),iterations=int(res.nit),objective=float(res.fun),
                maxiter=MAXITER,L2=L2,fit_status='converged' if res.success else 'stopped_without_convergence')
    return meta,arrays,reference


def arguments(meta,arrays):
    return (meta['code'],meta['features'],arrays.get('params',EMPTY64),arrays.get('edges',EMPTY64),
            arrays.get('feat',EMPTY16),arrays.get('thr',EMPTY64),arrays.get('left',EMPTY16),arrays.get('right',EMPTY16),
            arrays.get('leaf',EMPTY64),arrays.get('roots',EMPTY16))


@njit(cache=True)
def score_one(x,code,d,params,edges,feat,thr,left,right,leaf,roots):
    if code==1:
        s=params[3*d]
        for j in range(d):s+=(x[j]-params[j])/params[d+j]*params[2*d+j]
        return s
    if code==2:
        s=params[6*d]
        for j in range(d):
            z=(x[j]-params[j])/params[d+j]
            m0,m1=params[2*d+j],params[3*d+j];v0,v1=params[4*d+j],params[5*d+j]
            s-=.5*(math.log(v1/v0)+(z-m1)**2/v1-(z-m0)**2/v0)
        return s
    if code==3:
        s=params[d*16]
        for j in range(d):
            b=0
            while b<15 and x[j]>=edges[j*15+b]:b+=1
            s+=params[j*16+b]
        return s
    if code==4:
        start=2*d;bias=start+d*8;s=params[start+d*8+16]
        for h in range(8):
            v=params[bias+h]
            for j in range(d):v+=(x[j]-params[j])/params[d+j]*params[start+j*8+h]
            s+=max(0.,v)*params[bias+8+h]
        return s
    s=0.
    for root in roots:
        n=np.int64(root)
        while n>=0:n=np.int64(left[n] if x[feat[n]]<=thr[n] else right[n])
        s+=leaf[~n]
    return s


@njit(cache=True)
def native_scores(X,code,d,params,edges,feat,thr,left,right,leaf,roots):
    out=np.empty(len(X),np.float64)
    for i in range(len(X)):out[i]=score_one(X[i],code,d,params,edges,feat,thr,left,right,leaf,roots)
    return out


@njit(cache=True)
def score_checksum(X,idx,code,d,params,edges,feat,thr,left,right,leaf,roots):
    total=0.
    for i in idx:total+=score_one(X[i],code,d,params,edges,feat,thr,left,right,leaf,roots)
    return total

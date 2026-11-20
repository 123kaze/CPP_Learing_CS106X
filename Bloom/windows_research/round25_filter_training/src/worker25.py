"""Same MLP8 weights/dimensions, matched warm start and continuation limits."""
from loss25 import *  # thread settings before scientific imports
import argparse
import json
import time
import hashlib
import ctypes
from scipy.optimize import minimize
from scipy.stats import rankdata
from numba import get_num_threads
from statistics import median
import filter23 as F
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
SETTINGS={'url':(64,128),'caida_tcp_flow':(16,32)}


def ah(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()

def save(path,x):
    t=path.with_suffix('.json.tmp');t.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');t.replace(path)


def fixed_bytes(d):
    params=np.zeros(2*d+d*8+16+1,np.float64)
    header=np.zeros(6,np.int32)
    nav=[np.empty(4,np.float64),np.empty(5,np.uint8),np.empty(6,np.int64),np.empty(5,np.int64),np.empty(5,np.int64),np.empty(0,np.uint8)]
    return sys.getsizeof(params)+sys.getsizeof(header)+sum(sys.getsizeof(x) for x in nav)


def optimizer_record(res,seconds):
    return dict(success=bool(res.success),status=int(res.status),message=str(res.message),iterations=int(res.nit),
                function_evaluations=int(res.nfev),objective=float(res.fun),seconds=seconds,
                gradient_norm=float(np.linalg.norm(res.jac)))


def run(ds,seed,path):
    if ds.endswith('_tcp_flow'):
        sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
    library=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));get_threads=library.openblas_get_num_threads;get_threads.restype=ctypes.c_int
    assert get_threads()==get_num_threads()==1
    ids,y,X,features=F.C.load_dataset(ds);sp=F.C.make_split(ids,y,ds);train=sp['member_train']|sp['neg_train'];test=sp['neg_test']
    t=time.perf_counter();meta,warm,reference=M.fit('MLP8',X[train],y[train],seed);warm_s=time.perf_counter()-t
    d=X.shape[1];mean=warm['params'][:d];std=warm['params'][d:2*d];w0=warm['params'][2*d:].copy()
    Z=np.ascontiguousarray((X[train].astype(float)-mean)/std);yt=y[train].astype(float)
    scores0=forward(w0,Z)[0];cuts=np.quantile(scores0,[.2,.4,.6,.8])
    tau=max(.25,float((np.quantile(scores0,.75)-np.quantile(scores0,.25))/4))
    hashes=F.C.splitmix64(ids^np.uint64(F.C.H1_SALT))
    rng=np.random.default_rng(2301)
    request=np.concatenate([rng.choice(np.flatnonzero(test),90000,replace=True),rng.choice(np.flatnonzero(y),10000,replace=True)])
    rng.shuffle(request)
    F.D.allocate(np.ones(1000,np.int64),np.ones(1000),10000.)
    dummy=F.B.allocate(1,1024,0);F.B.insert_all(dummy,hashes[:1]);F.B.query_all(dummy,hashes[:2])
    rows=[];out=dict(status='running',dataset=ds,seed=seed,model='MLP8',members=int(y.sum()),train_rows=int(train.sum()),
                  test_negatives=int(test.sum()),features=features,parameters=len(warm['params']),warm_meta=meta,warm_train_s=warm_s,
                  soft_logit_cuts=cuts.tolist(),temperature=tau,request_sha256=ah(request),records=rows,
                  openblas_threads=1,numba_threads=1)
    for kib in SETTINGS[ds]:
        beta=float(A*(kib*1024-fixed_bytes(d))*8/int(y.sum()))
        assert beta>0
        options=dict(maxiter=100,ftol=1e-10,gtol=1e-6)
        branches={'BCE100':(w0.copy(),None)}
        # Equal common warm start; no selected training branch or additional hyperparameter sweep.
        order=('BCE200','FilterAware') if seed%2 else ('FilterAware','BCE200')
        for method in order:
            t=time.perf_counter()
            if method=='BCE200':res=minimize(M.mlp_objective,w0.copy(),args=(Z,yt),jac=True,method='L-BFGS-B',options=options)
            else:res=minimize(objective,w0.copy(),args=(Z,yt,cuts,tau,beta),jac=True,method='L-BFGS-B',options=options)
            elapsed=time.perf_counter()-t
            assert np.isfinite(res.fun) and np.isfinite(res.x).all()
            branches[method]=(res.x.copy(),optimizer_record(res,elapsed))
        # All branches at this budget are trained before using validation/test outcomes.
        for method in ('BCE100','BCE200','FilterAware'):
            weights,fit=branches[method]
            arrays={'params':np.concatenate([mean,std,weights])}
            assert arrays['params'].nbytes==warm['params'].nbytes
            train_score=forward(weights,Z)[0]
            proxy,_,details=surrogate_scores(train_score,yt,cuts,tau,beta)
            # Hardening the training-only soft regions is an additional diagnostic, not deployment.
            hard=np.searchsorted(cuts,train_score,side='left')
            hp=(np.bincount(hard[yt==1],minlength=5)+1)/(int((yt==1).sum())+5)
            hq=(np.bincount(hard[yt==0],minlength=5)+1)/(int((yt==0).sum())+5)
            hardJ,_,_,_=capped(hp,hq,beta)
            args=M.arguments(meta,arrays);M.native_scores(X[:2],*args)
            t=time.perf_counter();raw=M.native_scores(X,*args);score_prepare_s=time.perf_counter()-t
            assert np.isfinite(raw).all()
            sample=np.linspace(0,len(X)-1,10000,dtype=np.int64)
            expected=forward(weights,(X[sample].astype(float)-mean)/std)[0]
            assert np.allclose(raw[sample],expected,rtol=1e-8,atol=1e-8)
            t=time.perf_counter();layout,flags,memory=F.build(meta,arrays,raw,y,sp,hashes,kib);build_s=time.perf_counter()-t
            assert memory['model_bytes_with_headers']==sys.getsizeof(warm['params'])
            idx=np.arange(len(ids),dtype=np.int64)
            actual=F.query(X,hashes,idx,meta,arrays,layout)
            assert np.array_equal(actual,flags) and actual[y].all()
            copies={k:v.copy() for k,v in layout.items()};modelcopy={k:v.copy() for k,v in arrays.items()}
            assert np.array_equal(actual,F.query(X,hashes,idx,meta,modelcopy,copies))
            cs=M.score_checksum(X,request,*args);score_times=[];query_times=[]
            F.query(X,hashes,request,meta,arrays,layout)
            for _ in range(3):
                t=time.perf_counter_ns();got=M.score_checksum(X,request,*args);score_times.append((time.perf_counter_ns()-t)/len(request));assert got==cs
                t=time.perf_counter_ns();got=F.query(X,hashes,request,meta,arrays,layout);query_times.append((time.perf_counter_ns()-t)/len(request));assert np.array_equal(got,flags[request])
            ev=(y&~sp['member_train'])|test;pos=int(y[ev].sum());neg=int((~y[ev]).sum())
            auc=float((rankdata(raw[ev])[y[ev]].sum()-pos*(pos+1)/2)/(pos*neg))
            row=dict(method=method,budget_kib=kib,seed=seed,fp=int(flags[test].sum()),negatives=int(test.sum()),
                     **{k:v for k,v in memory.items() if k!='budget_kib'},optimizer=fit,
                     soft_training_J=details['J'],hard_training_J=hardJ,soft_active_regions=details['active_regions'],
                     beta=beta,soft_regularized_loss=objective(weights,Z,yt,cuts,tau,beta)[0],training_BCE=M.mlp_objective(weights,Z,yt)[0],
                     heldout_auc=auc,score_ns_all=score_times,score_ns_median=median(score_times),
                     query_ns_all=query_times,query_ns_median=median(query_times),score_prepare_s=score_prepare_s,filter_build_s=build_s,
                     training_s_charged=warm_s+(fit['seconds'] if fit else 0),member_fn=0,native_flags_exact=True,reload_exact=True,
                     model_sha256=ah(arrays['params']),flags_sha256=ah(flags),region_thresholds=layout['cuts'].tolist())
            rows.append(row)
            print(f'RESULT {ds} seed{seed} {kib}KiB {method}: FP={row["fp"]} soft={row["soft_training_J"]:.6g} hard={hardJ:.6g} query={row["query_ns_median"]:.1f}ns',flush=True)
        # Strong no-model reference, not forced to pay learned headers.
        data=F.B.allocate(int(y.sum()),kib*1024,0);F.B.insert_all(data,hashes[y]);flags=F.B.query_all(data,hashes)
        assert flags[y].all()
        rows.append(dict(method='BF',budget_kib=kib,seed=seed,fp=int(flags[test].sum()),negatives=int(test.sum()),total_bytes=sys.getsizeof(data)))
        save(path,out)
    assert len(rows)==8
    out['status']='complete';save(path,out)
    print(f'COMPLETE {ds} seed{seed}',flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--dataset',choices=SETTINGS,required=True);a.add_argument('--seed',type=int,choices=(1,2,3),required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
    assert not args.output.exists(),'Refuse output overwrite'
    run(args.dataset,args.seed,args.output)

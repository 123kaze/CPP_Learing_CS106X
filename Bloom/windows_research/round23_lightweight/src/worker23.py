"""Prespecified scorer replacement pilot on two real prepared datasets, no cache."""
from models23 import *  # sets threads before scientific imports
from pathlib import Path
import argparse
import json
import hashlib
import time
import resource
import platform
from statistics import median
from scipy.stats import rankdata
from numba import get_num_threads
import ctypes
import filter23 as F
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
DATASETS={'url':(64,128),'caida_tcp_flow':(16,32)}
TIMING_REPEATS=3


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()

def save(p,r):
    t=p.with_suffix('.json.tmp');t.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');t.replace(p)


def roc_auc(y,s):
    n=int(y.sum());m=len(y)-n
    if not n or not m:return None
    return float((rankdata(s)[y].sum()-n*(n+1)/2)/(n*m))


def measure(fn,expected):
    got=fn();assert np.array_equal(got,expected)
    times=[]
    for _ in range(TIMING_REPEATS):
        t=time.perf_counter_ns();got=fn();times.append((time.perf_counter_ns()-t)/len(expected))
        assert np.array_equal(got,expected)
    return dict(ns_per_query_all=times,median_ns_per_query=median(times),queries=len(expected))


def run(a):
    if a.dataset.endswith('_tcp_flow'):
        sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
    folder=F.C.CACHE/a.dataset
    for n in ('data.npz',):assert (folder/n).is_file(),'Prepared data required, no download/preparation'
    lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'))
    f=lib.openblas_get_num_threads;f.restype=ctypes.c_int
    assert f()==get_num_threads()==1
    ids,y,X,features=F.C.load_dataset(a.dataset)
    split=F.C.make_split(ids,y,a.dataset);train=split['member_train']|split['neg_train']
    val=split['neg_val'];test=split['neg_test']
    hashes=F.C.splitmix64(ids^np.uint64(F.C.H1_SALT))
    # Held-out member rows for classification diagnostics; all members are BF construction input.
    class_eval=(y&~split['member_train'])|test
    rng=np.random.default_rng(2301)
    neg_idx=rng.choice(np.flatnonzero(test),90000,replace=True)
    pos_idx=rng.choice(np.flatnonzero(y),10000,replace=True)
    requests=np.concatenate([neg_idx,pos_idx]);rng.shuffle(requests)
    # Warm static BF/DP kernels on tiny synthetic inputs, outside actual build timings.
    d=F.B.allocate(1,1024,0);F.B.insert_all(d,hashes[:1]);F.B.query_all(d,hashes[:2])
    F.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.)
    out=dict(status='running',dataset=a.dataset,rep=a.rep,features=features,rows=len(ids),members=int(y.sum()),
             train_rows=int(train.sum()),validation_negatives=int(val.sum()),test_negatives=int(test.sum()),
             request_count=len(requests),request_positive_count=10000,request_sha256=ah(requests),
             input_sha256=digest(folder/'data.npz'),python=platform.python_version(),numpy=np.__version__,
             openblas_threads=f(),numba_threads=get_num_threads(),models=[],filters=[])
    # Plain BF has no model preprocessing/headers; frozen round12 representation.
    for kib in DATASETS[a.dataset]:
        t=time.perf_counter();data=F.B.allocate(int(y.sum()),kib*1024,0);F.B.insert_all(data,hashes[y]);build_s=time.perf_counter()-t
        flags=F.B.query_all(data,hashes);assert flags[y].all()
        timing=measure(lambda:F.bf_query(data,hashes,requests),flags[requests])
        out['filters'].append(dict(model='BF',budget_kib=kib,fp=int(flags[test].sum()),negatives=int(test.sum()),
             total_bytes=sys.getsizeof(data),model_bytes_with_headers=0,model_payload_bytes=0,
             filter_payload_bytes=data.nbytes-32,metadata_and_headers_bytes=sys.getsizeof(data)-(data.nbytes-32),
             filter_build_s=build_s,native=timing,member_fn=0,roundtrip_checked=True,static_flags_sha256=ah(flags)))
    order=MODELS[a.rep:]+MODELS[:a.rep]
    for name in order:
        t=time.perf_counter();meta,arrays,reference=fit(name,X[train],y[train],1);train_s=time.perf_counter()-t
        args=arguments(meta,arrays)
        native_scores(X[:2],*args)
        t=time.perf_counter();raw=native_scores(X,*args);scoring_s=time.perf_counter()-t
        assert np.isfinite(raw).all()
        sampled=np.linspace(0,len(X)-1,10000,dtype=np.int64)
        assert np.allclose(raw[sampled],reference(X[sampled]),rtol=1e-8,atol=1e-8),(name,'native-model mismatch')
        copies={k:np.frombuffer(v.tobytes(),v.dtype).copy() for k,v in arrays.items()}
        assert np.array_equal(raw,native_scores(X,*arguments(meta,copies)))
        checksum=score_checksum(X,requests,*args);score_times=[]
        for _ in range(TIMING_REPEATS):
            t=time.perf_counter_ns();got=score_checksum(X,requests,*args);score_times.append((time.perf_counter_ns()-t)/len(requests))
            assert got==checksum
        model=dict(**meta,train_s=train_s,all_rows_score_s=scoring_s,model_arrays_sha256={k:ah(v) for k,v in arrays.items()},
                   model_payload_bytes=sum(v.nbytes for v in arrays.values()),model_bytes_with_headers=sum(sys.getsizeof(v) for v in arrays.values()),
                   score_ns_all=score_times,score_ns_median=median(score_times),heldout_auc=roc_auc(y[class_eval],raw[class_eval]),
                   reference_check_max_abs=float(np.max(np.abs(raw[sampled]-reference(X[sampled])))),native_reload_bit_exact=True)
        out['models'].append(model)
        for kib in DATASETS[a.dataset]:
            t=time.perf_counter();layout,flags,byte=F.build(meta,arrays,raw,y,split,hashes,kib);build_s=time.perf_counter()-t
            idx=np.arange(len(X),dtype=np.int64)
            real=F.query(X,hashes,idx,meta,arrays,layout)
            assert np.array_equal(real,flags),(name,'native-PLBF mismatch')
            assert real[y].all()
            reloaded={k:np.frombuffer(v.tobytes(),v.dtype).copy() for k,v in layout.items()}
            assert np.array_equal(real,F.query(X,hashes,idx,meta,copies,reloaded))
            timing=measure(lambda:F.query(X,hashes,requests,meta,arrays,layout),flags[requests])
            out['filters'].append(dict(model=name,**byte,fp=int(flags[test].sum()),negatives=int(test.sum()),
                  filter_build_s=build_s,native=timing,member_fn=0,roundtrip_checked=True,static_flags_sha256=ah(flags)))
            print(f'FILTER {a.dataset} rep{a.rep} {name} {kib}KiB: FP={int(flags[test].sum())} model={byte["model_bytes_with_headers"]}B query={timing["median_ns_per_query"]:.1f}ns',flush=True)
        save(a.output,out)
        print(f'TRAIN {name}: {train_s:.3f}s status={meta["fit_status"]}',flush=True)
    out.update(status='complete',peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save(a.output,out)
    print(f'COMPLETE {a.dataset} rep{a.rep}',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=DATASETS,required=True);p.add_argument('--rep',type=int,choices=range(3),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(),'Refuse output overwrite'
    run(a)

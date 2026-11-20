"""Small static cell-table trial; all declared configurations evaluated, no cherry-picking."""
from cells24 import *
import json
import time
import hashlib
import ctypes
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
SETTINGS={'url':(64,128),'caida_tcp_flow':(16,32)}


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()

def save(p,r):
    tmp=p.with_suffix('.json.tmp');tmp.write_text(json.dumps(r,indent=2)+'\n');tmp.replace(p)


def main():
    frozen=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for path,h in frozen[section].items():assert digest(BLOOM/path)==h,path
    from numba import get_num_threads
    library=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'))
    f=library.openblas_get_num_threads;f.restype=ctypes.c_int
    assert f()==get_num_threads()==1
    D.allocate(np.ones(256,np.int64),np.ones(256),10000.)
    output=ROOT/'results/rows.json';assert not output.exists(),'Refuse existing output'
    result=dict(status='running',rows=[],openblas_threads=1,numba_threads=1)
    for ds,budgets in SETTINGS.items():
        if ds.endswith('_tcp_flow'):
            sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
        ids,y,X,features=C.load_dataset(ds);split=C.make_split(ids,y,ds)
        hashes=C.splitmix64(ids^np.uint64(C.H1_SALT));test=split['neg_test']
        feature=[features.index(x) for x in FEATURES[ds]]
        rng=np.random.default_rng(2301)
        request=np.concatenate([rng.choice(np.flatnonzero(test),90000,replace=True),rng.choice(np.flatnonzero(y),10000,replace=True)])
        rng.shuffle(request)
        baseline=json.loads((WR/f'round23_lightweight/results/main/{ds}_rep0.json').read_text())
        assert ah(request)==baseline['request_sha256']
        allidx=np.arange(len(X),dtype=np.int64)
        for rep in range(3):
            for bins in (16,32):
                for kib in budgets:
                    begin=time.perf_counter();arrays,flags,meta=fit_build(X,y,split,hashes,feature,bins,kib);build_s=time.perf_counter()-begin
                    actual=query(X,hashes,allidx,**arrays);assert np.array_equal(actual,flags)
                    assert actual[y].all()
                    check=router_checksum(X,request,arrays['header'],arrays['edges'],arrays['route'])
                    query(X,hashes,request,**arrays)
                    rt=[];ft=[]
                    for _ in range(3):
                        t=time.perf_counter_ns();got=router_checksum(X,request,arrays['header'],arrays['edges'],arrays['route']);rt.append((time.perf_counter_ns()-t)/len(request));assert got==check
                        t=time.perf_counter_ns();got=query(X,hashes,request,**arrays);ft.append((time.perf_counter_ns()-t)/len(request));assert np.array_equal(got,flags[request])
                    plain=next(x for x in baseline['filters'] if x['model']=='BF' and x['budget_kib']==kib)
                    result['rows'].append(dict(dataset=ds,budget_kib=kib,bins_per_feature=bins,rep=rep,feature_names=list(FEATURES[ds]),
                        **meta,fit_build_s=build_s,fp=int(flags[test].sum()),negatives=int(test.sum()),
                        bf_reference_fp=plain['fp'],fp_over_bf=(int(flags[test].sum())+1)/(plain['fp']+1),
                        router_ns_all=rt,router_ns_median=median(rt),filter_ns_all=ft,filter_ns_median=median(ft),
                        members_verified=True,native_matches_frozen_flags=True,request_sha256=ah(request),flags_sha256=ah(flags)))
                    save(output,result)
                    print(f'CELL {ds} {bins}x{bins} {kib}KiB rep{rep}: FP={int(flags[test].sum())} BF={plain["fp"]} routebytes={meta["router_bytes"]} query={median(ft):.1f}ns',flush=True)
    assert len(result['rows'])==24
    for path,h in frozen['sources'].items():assert digest(BLOOM/path)==h
    result['status']='complete';save(output,result)
    print('ROUND24 COMPLETE:24 table/filter builds, actual bytes/native queries, no cache or weighted training claim',flush=True)


if __name__=='__main__':main()

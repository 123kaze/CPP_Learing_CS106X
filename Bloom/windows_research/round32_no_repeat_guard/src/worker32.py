import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from guard32 import *
sys.path.insert(0,str(WR/'round19_gt_fix/src'))
from summarize19 import summarize19
import json,csv,hashlib,ctypes,resource
from numba import get_num_threads
SETTINGS={'cod':(256,1024,4096),'url':(64,128,256),'caida':(128,256,1024,2048),'shalla':(256,1024,2048,4096)}
CONTROL={'cod':1024,'url':128,'caida':256,'shalla':1024}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.json.tmp');q.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');q.replace(p)


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in f['sources'].items():assert sha(BLOOM/rel)==h,rel
    return sha(ROOT/'plan/freeze.json')


def archive(ds,kib):
    allrows={}
    for path,method in ((WR/f'round5_dp/results/rows_{ds}_{kib}.csv','Gama'),(WR/f'round6_bucket/results/main/rows_{ds}_{kib}.csv','RA6')):
        with path.open() as f:
            for r in csv.DictReader(f):
                if r['method']==method:allrows[r['workload'],int(r['seed']),method]=r
    return allrows


def payload(s,scores,c,reference_arrays=None):
    st=c['structure'];td=E5.tree(s,scores,c['trees']);reg=E5.D.region_of_segment(st.b)
    off=np.concatenate([[0],np.cumsum(st.m)]).astype(np.int64);bits=np.zeros((int(off[-1])+7)//8,np.uint8)
    E5.R.packed_build(s.h1m,reg[td.seg_m].astype(np.int32),off,st.m,st.k,bits)
    assert E5.R.packed_query(s.h1m,reg[td.seg_m].astype(np.int32),st.kind,off,st.m,st.k,bits).all()
    assert np.array_equal(E5.R.packed_query(s.h1q,st.q_region,st.kind,off,st.m,st.k,bits),st.fp_static)
    assert st.used_bytes<=st.budget_bytes
    arrays={'bounds':st.b,'kind':st.kind,'offsets':off,'m':st.m,'k':st.k,'bits':bits,'flags':st.fp_static,
            **{'model_'+k:v for k,v in E5.R._MODEL_ARRAYS[s.name,c['trees']].items()}}
    if reference_arrays is not None:
        assert arrays.keys()==reference_arrays.keys()
        for key,value in arrays.items():
            ref=reference_arrays[key]
            assert value.dtype==ref.dtype and value.shape==ref.shape and np.array_equal(value.view(np.uint8),ref.view(np.uint8)),key
    hashes={k:dict(sha256=ah(v),dtype=str(v.dtype),shape=list(v.shape)) for k,v in arrays.items()}
    return dict(trees=c['trees'],cache_bytes=c['cache_bytes'],total_bytes=st.used_bytes,hashes=hashes,member_fn=0),arrays


def run(ds,out):
    freeze=check();lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));f=lib.openblas_get_num_threads;f.restype=ctypes.c_int;assert f()==get_num_threads()==1
    start=time.perf_counter();s,scores,safe=E5.load(ds);load_s=time.perf_counter()-start;specs=dict(E5.workload_specs(len(s.h1q)))
    result=dict(status='running',dataset=ds,freeze_sha256=freeze,load_s=load_s,native_threads=1,cases=[],reference_budgets=[])
    references={};old={}
    for kib in SETTINGS[ds]:
        t=time.perf_counter();c=E5.gama(E5.candidates(s,scores,kib,fracs=(0.,)));build_s=time.perf_counter()-t
        t=time.perf_counter();p,arrays=payload(s,scores,c);hash_s=time.perf_counter()-t
        references[kib]=(c,p,arrays);old[kib]=archive(ds,kib);result['reference_budgets'].append(dict(budget_kib=kib,build_select_s=build_s,payload_check_s=hash_s,**p))
    for workload in ('每key一次','全新对抗'):
        for seed in range(5):
            t=time.perf_counter();base=E5.base_stream(s,workload,specs[workload],seed);stream_s=time.perf_counter()-t
            cut=len(base)//4;learn,tail=base[:cut],base[cut:]
            t=time.perf_counter();lm=summarize19(learn);count_s=time.perf_counter()-t;assert no_repeat(lm)
            for kib in SETTINGS[ds]:
                t=time.perf_counter();c,info=select(s,scores,lm,kib,len(tail));selection_s=time.perf_counter()-t
                t=time.perf_counter();p,_=payload(s,scores,c,references[kib][2]);check_s=time.perf_counter()-t
                assert p==references[kib][1],(ds,kib,workload,seed,'Byte-accounted payload differs')
                t=time.perf_counter();fp=E5.evaluate(c,tail,s,safe)['fp'];eval_s=time.perf_counter()-t
                for method in ('Gama','RA6'):
                    row=old[kib][workload,seed,method];assert fp==int(row['fp_tail']) and c['trees']==int(row['trees']),(ds,kib,workload,seed,method)
                record=dict(budget_kib=kib,workload=workload,seed=seed,learning_queries=len(learn),tail_queries=len(tail),stream_sha256=ah(base),
                            fp=fp,trees=c['trees'],cache_bytes=c['cache_bytes'],total_bytes=c['structure'].used_bytes,
                            member_fn=0,gama_payload_bit_equal=True,original_Gama_FP_equal=True,original_RA6_FP_equal=True,
                            payload=p,selection_info=info,stream_prepare_s=stream_s,count_s=count_s,select_build_s=selection_s,payload_check_s=check_s,tail_eval_s=eval_s)
                result['cases'].append(record);save(out,result)
                print('NO_REPEAT VERIFIED',ds,kib,workload,seed,'FP',fp,'trees',c['trees'],flush=True)
    # Independent live repeated control: wrapper must select exactly the frozen RA6 result.
    t=time.perf_counter();base=E5.base_stream(s,'zipf1.0-全部',specs['zipf1.0-全部'],0);cut=len(base)//4;lm=summarize19(base[:cut]);assert not no_repeat(lm)
    control_prepare_s=time.perf_counter()-t;kib=CONTROL[ds];H=len(base)-cut
    t=time.perf_counter();a,ai=ra6.select6(s,scores,lm,kib,H);old_s=time.perf_counter()-t
    t=time.perf_counter();b,bi=select(s,scores,lm,kib,H);new_s=time.perf_counter()-t
    pa,aa=payload(s,scores,a);pb,_=payload(s,scores,b,aa);assert pa==pb and bi['path']=='unchanged_RA6'
    afp=E5.evaluate(a,base[cut:],s,safe)['fp'];bfp=E5.evaluate(b,base[cut:],s,safe)['fp'];assert afp==bfp
    result['repeated_control']=dict(workload='zipf1.0-全部',seed=0,budget_kib=kib,fp=afp,payload_bit_equal=True,prepare_s=control_prepare_s,
                                    original_select_s=old_s,guarded_select_s=new_s,old_info=ai,new_info=bi,payload=pa)
    assert len(result['cases'])==len(SETTINGS[ds])*10;check();result.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);save(out,result)
    print('COMPLETE',ds,len(result['cases']),'no-repeat cases plus repeated control',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=SETTINGS);p.add_argument('output',type=Path);a=p.parse_args();assert not a.output.exists()
    try:run(a.dataset,a.output)
    except Exception as e:save(a.output.with_suffix('.error.json'),dict(status='failed',error=repr(e)));raise

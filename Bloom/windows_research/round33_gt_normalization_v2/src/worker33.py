import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from normalize33 import *
sys.path.insert(0,str(WR/'round32_no_repeat_guard/src'))
from worker32 import payload
import csv,ctypes,resource
from numba import get_num_threads


def cases():
    rows=[dict(dataset=r['dataset'],budget_kib=r['budget_kib'],workload=r['workload'],seed=r['seed'],cohort='GT-gap affected') for r in json.loads((WR/'round18_gt_audit/results/affected_cases.json').read_text())]
    for ds in ('caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow'):rows.append(dict(dataset=ds,budget_kib=24,workload='真实轨迹',seed=0,cohort='real_trace'))
    for ds,k in (('caida_tcp_flow',32),('mawi2020_tcp_flow',64),('mawi2021_tcp_flow',41),('mawi2022_tcp_flow',64)):rows.append(dict(dataset=ds,budget_kib=k,workload='真实轨迹',seed=0,cohort='TCP_only'))
    for ds,k in (('cod',1024),('url',128),('caida',256),('shalla',1024)):
        for w in ('每key一次','全新对抗'):rows.append(dict(dataset=ds,budget_kib=k,workload=w,seed=0,cohort='no_repeat'))
    assert len(rows)==30 and len({(r['dataset'],r['budget_kib'],r['workload'],r['seed']) for r in rows})==30
    return rows


DATASETS=tuple(dict.fromkeys(r['dataset'] for r in cases()))


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in f['sources'].items():assert sha(BLOOM/rel)==h,rel
    return sha(ROOT/'plan/freeze.json')


def reference_rows():
    with (WR/'round19_gt_fix/results/updated_main_comparisons.csv').open() as f:
        return {(r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']),r['cache']):r for r in csv.DictReader(f)}


def evaluate(c,stream,setup,safe,mode):
    cache=CACHES[mode];spec=cache.layout(c['cache_bytes']);data=cache.allocate(spec)
    aux=safe if mode=='index' else np.empty(0,np.bool_)
    cnt=cache.replay(stream,setup.h1q,aux,c['structure'].fp_static,data,spec['buckets'],spec['prefix_bits'],spec['Q'],spec['ob'],spec['slot_bits'],4,spec['handbits'],2**62,np.empty(0,np.int64),np.empty(0,np.bool_))
    assert cnt[5]==len(stream) and cnt[6]==0
    fn=cache.count_member_hits(data,setup.h1m,spec['buckets'],spec['prefix_bits'],spec['Q'],spec['ob'],spec['slot_bits'],4);assert fn==0
    return dict(zip(('fp','hits','inserts','evictions','bypasses','processed','cutoff','occupied'),map(int,cnt[:8]))),dict(member_hits_final=int(fn),cache_state_sha256=ah(data),cache_physical_bytes=spec['allocated_bytes'])


def run(ds,mode,out):
    frozen=check();lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));f=lib.openblas_get_num_threads;f.restype=ctypes.c_int;assert f()==get_num_threads()==1
    if ds.endswith('_tcp_flow'):
        sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
    E5.K=CACHES[mode]
    start=time.perf_counter();s,scores,safe=E5.load(ds);load_s=time.perf_counter()-start;refs=reference_rows();specs=dict(E5.workload_specs(len(s.h1q)))
    selected=[r for r in cases() if r['dataset']==ds]
    result=dict(status='running',dataset=ds,cache=mode,freeze_sha256=frozen,load_s=load_s,native_threads=1,cases=[])
    for case in selected:
        kib,w,seed=case['budget_kib'],case['workload'],case['seed']
        timer=time.perf_counter();base=E5.base_stream(s,w,None if w=='真实轨迹' else specs[w],seed);stream_s=time.perf_counter()-timer
        cut=len(base)//4;learn,tail=base[:cut],base[cut:]
        timer=time.perf_counter();raw=summarize19(learn);count_s=time.perf_counter()-timer;original_rate=raw.rate.copy()
        item=dict(**case,cache=mode,learning_queries=len(learn),tail_queries=len(tail),stream_sha256=ah(base),stream_s=stream_s,count_s=count_s,arms={})
        reference_payload=None;reference_arrays=None;reference_rank=None
        for arm in ARMS:
            c,info=select(s,scores,raw,kib,len(tail),arm)
            assert np.array_equal(raw.rate.view(np.uint8),original_rate.view(np.uint8)),'Normalization mutated control'
            timer=time.perf_counter();p,arrays=payload(s,scores,c,reference_arrays if case['cohort']=='no_repeat' and arm!='GT19' else None)
            payload_equal=(arm=='GT19') or (all(p[k]==reference_payload[k] for k in ('trees','cache_bytes','total_bytes')) and
                all(arrays[k].dtype==reference_arrays[k].dtype and arrays[k].shape==reference_arrays[k].shape and np.array_equal(arrays[k].view(np.uint8),reference_arrays[k].view(np.uint8)) for k in arrays))
            if arm!='GT19':assert payload_equal==(p==reference_payload)
            payload_s=time.perf_counter()-timer
            timer=time.perf_counter();counts,cachecheck=evaluate(c,tail,s,safe,mode);evaluation_s=time.perf_counter()-timer
            rank={(r['trees'],r['frac']):r['rank'] for r in info['table']}
            if arm=='GT19':
                assert counts['fp']==int(refs[ds,kib,w,seed,mode]['repaired_ra_fp']),(case,mode,'GT19 control mismatch')
                reference_payload=p;reference_arrays=arrays;reference_rank=rank
            else:
                assert rank.keys()==reference_rank.keys()
                if case['cohort']=='no_repeat':assert p==reference_payload and counts['fp']==item['arms']['GT19']['fp']
            top={key for key,r in rank.items() if r<5};oldtop={key for key,r in reference_rank.items() if r<5}
            item['arms'][arm]=dict(**counts,**cachecheck,trees=c['trees'],frac=c['frac'],total_bytes=c['structure'].used_bytes,
                                  payload=p,payload_check_s=payload_s,evaluate_s=evaluation_s,info=info,
                                  same_configuration_as_GT19=(c['trees'],c['cache_bytes'])==(reference_payload['trees'],reference_payload['cache_bytes']),
                                  same_payload_as_GT19=payload_equal,rank_positions_changed=sum(rank[k]!=reference_rank[k] for k in rank),top5_overlap=len(top&oldtop))
            assert c['structure'].used_bytes<=kib*1024
            print('ARM',ds,mode,kib,w,seed,arm,'mass',info['normalization']['total_mass'],'FP',counts['fp'],'trees',c['trees'],'frac',c['frac'],flush=True)
        result['cases'].append(item);save(out,result)
    assert len(result['cases'])==len(selected);check();result.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);save(out,result)
    print('COMPLETE',ds,mode,len(selected)*3,'arm records',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=DATASETS);p.add_argument('cache',choices=CACHES);p.add_argument('output',type=Path);a=p.parse_args();assert not a.output.exists()
    try:run(a.dataset,a.cache,a.output)
    except Exception as e:save(a.output.with_suffix('.error.json'),dict(status='failed',error=repr(e)));raise

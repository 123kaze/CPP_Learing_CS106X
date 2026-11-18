"""Synchronous real RocksDB Get loop; no labels/static flags in decision path."""
from common16 import *
import argparse
import resource
import time
import traceback
import numpy as np
import rocksdict as Rocks
from native16 import make_native,KEYS,probe_all


def main(a):
    out=dict(status='running',method=a.method,workload=a.workload,cache_regime=a.cache,rep=a.rep,pilot=a.pilot)
    db=None
    try:
        data=np.load(ROOT/'inputs/requests.npz');ids=data['ids'];X=data['X'];nm=int(data['members'])
        stream=np.load(ROOT/f'inputs/{a.workload}_tail.npy')
        if a.pilot:stream=stream[:2048]
        # Keys and features are request input. There is no per-query FP lookup or true-membership input to the native filter.
        keys=[key_bytes(i) for i in ids]
        native=None;meta={};arrays=None
        if a.method!='Direct':
            p=ROOT/'inputs'/('smoke_filters' if a.pilot else 'filters')/f'{a.workload}_rep{a.rep}_{a.method}.npz'
            meta=json.loads(p.with_suffix('.json').read_text());assert digest(p)==meta['artifact_sha256']
            with np.load(p) as f:arrays={k:f[k].copy() for k in KEYS}
            native=make_native(arrays,a.method=='BFCache',meta['cache_bytes'])
            probe_all(native,ids[:2],X[:2]);native.feedback()  # JIT only; disposable state
            native=make_native(arrays,a.method=='BFCache',meta['cache_bytes'])
        opts,cache=db_options(CACHES[a.cache])
        db=Rocks.Rdict(str(ROOT/'db/url'),opts,column_families={'default':opts},access_type=Rocks.AccessType.read_only())
        assert db.property_int_value('rocksdb.estimate-num-keys')==nm
        assert db.property_int_value('rocksdb.cur-size-active-mem-table')<1024*1024
        warm_start=time.perf_counter()
        for i in range(nm):assert db.get(keys[i]) is not None
        out['database_warm_s']=time.perf_counter()-warm_start
        # Verify EFFECTIVE configuration, not merely the requested capacity variable.
        assert cache.get_usage() > 0
        assert cache.get_usage() == db.property_int_value('rocksdb.block-cache-usage')
        assert db.property_int_value('rocksdb.block-cache-capacity') == CACHES[a.cache]
        c0,_=stats(opts)
        for i in np.linspace(0,nm-1,2000,dtype=np.int64):assert db.get(keys[i]) is not None
        c1,_=stats(opts)
        dh=c1['rocksdb.block.cache.data.hit']-c0['rocksdb.block.cache.data.hit']
        dm=c1['rocksdb.block.cache.data.miss']-c0['rocksdb.block.cache.data.miss']
        rate=dh/max(1,dh+dm)
        assert rate >= .95 if a.cache=='fit' else rate <= .20, ('cache-regime-not-achieved',a.cache,rate)
        c0,_=stats(opts)
        for i in range(nm,nm+2000):assert db.get(keys[i]) is None
        c1,_=stats(opts)
        assert c1['rocksdb.bloom.filter.useful']-c0['rocksdb.bloom.filter.useful'] >= 1900
        out['configuration_check']=dict(effective_cache_capacity=db.property_int_value('rocksdb.block-cache-capacity'),
            cache_object_equals_db_usage=True,positive_probe_hit_rate=rate,
            bloom_useful_of_2000_misses=c1['rocksdb.bloom.filter.useful']-c0['rocksdb.bloom.filter.useful'],
            explicit_default_column_family=True)
        # All methods see identical full-member database warmup and an empty external cache.
        before,raw_before=stats(opts);usage0=resource.getrusage(resource.RUSAGE_SELF)
        lat=np.empty(len(stream),np.int64);answer=np.zeros(len(stream),np.bool_)
        invalid_value=np.zeros(len(stream),np.bool_)
        calls=misses=hits=rejects=updates=0
        cpu=time.process_time();start=time.perf_counter_ns()
        if native is None:
            for j,i in enumerate(stream):
                t=time.perf_counter_ns();value=db.get(keys[i]);calls+=1
                if value is None:misses+=1
                else:
                    answer[j]=True;invalid_value[j]=(len(value)!=VALUE_BYTES or value[:8]!=keys[i])
                lat[j]=time.perf_counter_ns()-t
        else:
            for j,i in enumerate(stream):
                t=time.perf_counter_ns();decision=native.probe(ids[i],X[i])
                if decision==1:
                    value=db.get(keys[i]);calls+=1
                    if value is None:
                        misses+=1
                        # Only this backend-returned None authorizes a negative cache update.
                        updates+=bool(native.feedback())
                    else:
                        answer[j]=True;invalid_value[j]=(len(value)!=VALUE_BYTES or value[:8]!=keys[i])
                elif decision==2:hits+=1
                else:rejects+=1
                lat[j]=time.perf_counter_ns()-t
        elapsed=(time.perf_counter_ns()-start)/1e9;cpu=time.process_time()-cpu
        usage1=resource.getrusage(resource.RUSAGE_SELF);after,raw_after=stats(opts)
        delta={k:v-before.get(k,0) for k,v in after.items()}
        expected=stream<nm  # first use of true membership during measured-query processing is AFTER timing
        assert np.array_equal(answer,expected),'wrong database answer (FP/FN)'
        assert not invalid_value.any(),'incorrect returned value'
        assert calls+hits+rejects==len(stream)
        assert calls==int(expected.sum())+misses
        assert delta['rocksdb.number.keys.read']==calls
        if not a.pilot and a.method!='Direct':assert misses==meta['expected_db_negative_misses']
        if native is not None:assert (probe_all(native,ids[:nm],X[:nm])==1).all()
        hit=delta.get('rocksdb.block.cache.data.hit',0);miss=delta.get('rocksdb.block.cache.data.miss',0)
        out.update(status='ok',queries=len(stream),positive_queries=int(expected.sum()),negative_queries=int((~expected).sum()),
                   seconds=elapsed,cpu_s=cpu,throughput_qps=len(stream)/elapsed,mean_us=elapsed*1e6/len(stream),
                   timed_request_mean_us=float(lat.mean()/1000),p50_us=float(np.quantile(lat,.5)/1000),
                   p95_us=float(np.quantile(lat,.95)/1000),p99_us=float(np.quantile(lat,.99)/1000),
                   db_calls=calls,db_negative_misses=misses,cache_hits=hits,filter_rejections=rejects,cache_insertions=updates,
                   returned_members=int(answer.sum()),wrong_answers=0,invalid_values=0,member_fn_after_run=0,
                   block_cache_capacity=CACHES[a.cache],block_cache_usage=cache.get_usage(),
                   data_block_hit_rate=hit/max(1,hit+miss),rocksdb_statistics_delta=delta,
                   minor_faults=usage1.ru_minflt-usage0.ru_minflt,major_faults=usage1.ru_majflt-usage0.ru_majflt,
                   whole_process_peak_rss_bytes=usage1.ru_maxrss,filter=meta,
                   stream_sha256=ah(stream),input_keys_sha256=ah(ids),python=sys.version,numpy=np.__version__,binding='rocksdict==0.3.29',
                   note='Real Get results govern feedback. Static read-only snapshot; OS page cache not evicted. Features precomputed request input; Python/Numba FFI overhead included.')
        a.output.with_suffix('.rocksdb_stats.txt').write_text(raw_after)
        np.savez_compressed(a.output.with_suffix('.latency.npz'),latency_ns=lat)
        out['latency_sha256']=digest(a.output.with_suffix('.latency.npz'))
        print(f'QUERY {a.method} {a.workload} {a.cache} rep{a.rep}: {elapsed:.3f}s calls={calls} negative_misses={misses} data_hit_rate={out["data_block_hit_rate"]:.3f}',flush=True)
    except Exception:
        out['status']='error';out['error']=traceback.format_exc();print(out['error'],flush=True)
    finally:
        if db is not None:db.close()
    save(a.output,out)
    if out['status']!='ok':raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--method',choices=METHODS,required=True)
    p.add_argument('--workload',choices=WORKLOADS,required=True);p.add_argument('--cache',choices=CACHES,required=True)
    p.add_argument('--rep',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pilot',action='store_true')
    a=p.parse_args()
    if a.output.exists():p.error('Output exists; refusing overwrite')
    a.output.parent.mkdir(parents=True,exist_ok=True);main(a)

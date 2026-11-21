import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cost34 import *
from summarize19 import summarize19
from online31 import feedback_absent
import json,sqlite3,tempfile,ctypes,resource
from numba import get_num_threads


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in f['sources'].items():assert sha(BLOOM/rel)==h,rel
    return sha(ROOT/'plan/freeze.json')


def prepare_fixed(ds):
    prior_path=WR/f'round31_sqlite_online/results/{ds}.json';prior=json.loads(prior_path.read_text());assert prior['status']=='complete'
    start=time.perf_counter();s,scores,safe=E5.load(ds);kib=SETTINGS[ds]
    workload='真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部';spec=None if workload=='真实轨迹' else dict(E5.workload_specs(len(s.h1q)))[workload]
    base=E5.base_stream(s,workload,spec,0);cut=len(base)//4;lm=summarize19(base[:cut]);old=J.RA.ra4.summarize(base[:cut])
    assert np.array_equal(lm.rate,old.rate) and lm.N1==old.N1
    ra,_=J.ra6.select6(s,scores,lm,kib,len(base)-cut)
    bf=B.build(s,kib,prior['methods']['BF+Cache']['cache_frac'],K)
    space=J.space_of(s,ds);requests=J.mixed(base[cut:cut+200000],space.nm,.1,np.random.default_rng(8));keys=space.ids.view(np.int64)
    assert len(requests)==200000 and ah(requests)==prior['request_sha256'] and ah(keys[requests])==prior['request_key_sha256']
    filters={};references={}
    for name,c in (('RA6',ra),('BF+Cache',bf)):
        previous=prior['methods'][name];st=c['structure']
        assert (c['trees'],c['frac'],c['cache_bytes'],st.used_bytes,ah(st.fp_static))==(previous['trees'],previous['cache_frac'],previous['cache_bytes'],previous['original_reserved_bytes'],previous['static_flags_sha256'])
        legacy=J.Exe(s,scores,c,space) if name=='RA6' else None
        flt=Online(c,space,legacy)
        flags=flt.all_probes(np.arange(len(space.h),dtype=np.int64));assert (flags[:space.nm]==1).all() and np.array_equal(flags[space.nm:]==1,st.fp_static)
        ref=original_reference(flt,space,requests,legacy)
        assert ah(ref['mask'])==previous['expected_mask_sha256'] and ah(ref['state'])==previous['expected_cache_sha256']
        assert ref['backend_calls']==previous['expected_backend_calls'] and ref['fp']==previous['expected_fp']
        flt.reset();flt.probe(int(requests[0]));flt.reset()
        filters[name]=flt;references[name]=ref
    feedback_absent(np.uint64(0),np.empty(0,np.uint64),np.empty(0,np.uint64),0,32,0,0,2)
    return space,requests,keys,filters,references,prior,dict(prepare_and_reconstruct_s=time.perf_counter()-start,round31_sha256=sha(prior_path),gt19_equal_original=True)


def run(ds,out):
    frozen=check();start=time.perf_counter()
    lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));f=lib.openblas_get_num_threads;f.restype=ctypes.c_int;assert f()==get_num_threads()==1
    space,requests,keys,filters,refs,prior,prep=prepare_fixed(ds)
    result=dict(status='running',dataset=ds,budget_kib=SETTINGS[ds],freeze_sha256=frozen,request_sha256=ah(requests),queries=len(requests),members=space.nm,
                member_queries=prior['member_queries'],native_threads=1,preparation=prep,round31_configurations={m:prior['methods'][m] for m in METHODS},timings=[])
    query='SELECT value FROM kv WHERE key = ?'
    with tempfile.TemporaryDirectory(prefix='backend_cost34_') as temp:
        t=time.perf_counter();con=sqlite3.connect(str(Path(temp)/'kv.sqlite'));con.execute('CREATE TABLE kv (key INTEGER PRIMARY KEY, value BLOB NOT NULL)')
        con.executemany('INSERT INTO kv VALUES (?,?)',((int(k),b'\0'*32) for k in keys[:space.nm]));con.commit()
        assert con.execute('SELECT COUNT(*) FROM kv').fetchone()[0]==space.nm
        result['database']=dict(create_s=time.perf_counter()-t,page_count=con.execute('PRAGMA page_count').fetchone()[0],page_size=con.execute('PRAGMA page_size').fetchone()[0],
                                cache_size=con.execute('PRAGMA cache_size').fetchone()[0],sqlite_version=sqlite3.sqlite_version)
        previous_db=next(d for d in prior['databases'] if d['backend']=='file')
        assert result['database']['page_count']==previous_db['page_count'] and result['database']['page_size']==previous_db['page_size']
        t=time.perf_counter()
        for _ in range(2000):assert con.execute(query,(int(keys[0]),)).fetchone() is not None
        result['database']['warmup_s']=time.perf_counter()-t
        for rep in range(3):
            deltas=DELAYS_US[rep:]+DELAYS_US[:rep]
            for pos,delta in enumerate(deltas):
                methods=METHODS if (rep+pos)%2==0 else METHODS[::-1]
                for order,method in enumerate(methods):
                    flt=filters[method];flt.reset();mask=np.zeros(len(requests),np.uint8)
                    cursor=BackendCostCursor(con.cursor(),delta)
                    r=online_run(cursor,query,keys,requests,flt,mask);cursor.close();delay=cursor.stats();ref=refs[method]
                    assert cursor.calls==r['backend_calls'] and r['members_found']==prior['member_queries']
                    for key in ('backend_calls','fp','members_found','cache_hits'):assert r[key]==ref[key]
                    assert np.array_equal(mask,ref['mask']) and np.array_equal(flt.data,ref['state'])
                    p=flt.spec;assert K.count_member_hits(flt.data,space.sorted_m,p['buckets'],40,p['Q'],p['ob'],p['slot_bits'],4)==0
                    if delta:assert delay['observed_busy_wait_ns_total']>=delay['requested_extra_ns_total'] and delay['observed_min_wait_ns']>=delta*1000
                    else:assert delay['observed_busy_wait_ns_total']==0 and delay['observed_min_wait_ns'] is None
                    row=dict(rep=rep,delay_us=delta,delay_order=pos,method_order=order,method=method,**r,**delay,
                             accepted_mask_sha256=ah(mask),cache_sha256=ah(flt.data),same_mask_as_round31=True,same_cache_as_round31=True,member_fn=0)
                    result['timings'].append(row);save(out,result)
                    print(f'TIMED {ds} delta={delta}us rep={rep} {method}: {r["ns_per_query"]/1000:.3f}us/query, SQL={r["backend_calls"]}, mean_added_wait={delay["observed_mean_wait_ns"]/1000:.3f}us',flush=True)
        con.close()
    assert len(result['timings'])==36;check();result.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);save(out,result)
    print('COMPLETE',ds,'36timings',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=SETTINGS);p.add_argument('output',type=Path);a=p.parse_args();assert not a.output.exists()
    try:run(a.dataset,a.output)
    except Exception as e:save(a.output.with_suffix('.error.json'),dict(status='failed',error=repr(e)));raise

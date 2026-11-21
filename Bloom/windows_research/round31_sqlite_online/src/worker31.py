import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from online31 import *
from summarize19 import summarize19
import sqlite3
import tempfile
import platform
import ctypes
import resource
from numba import get_num_threads
from statistics import median

SETTINGS={'cod':1024,'url':128,'caida':256,'shalla':1024,'caida_flow':24,'mawi2020_flow':24,'mawi2021_flow':24,'mawi2022_flow':24}
REPS=3
Q=200000


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in f['sources'].items():assert sha(BLOOM/rel)==h,rel
    return sha(ROOT/'plan/freeze.json')


def original_reference(flt,space,requests,legacy=None):
    timer=time.perf_counter()
    if flt is None:
        acc=np.ones(len(requests),np.uint8);state=np.empty(0,np.uint64)
        calls=len(requests);found=int(space.member[requests].sum());fp=calls-found;hits=0
    elif legacy is not None:
        state=legacy.fresh_cache();cnt,acc=legacy.run(requests,0,len(requests),2,state)
        calls,fp,hits=int(cnt[0]),int(cnt[1]),int(cnt[3]);found=calls-fp;assert cnt[2]==0
    else:
        p=flt.spec;state=K.allocate(p)
        cnt,acc=reference_bf(requests,space.h,space.member,flt.c['structure'].data,state,space.sorted_m,p['buckets'],p['Q'],p['ob'],p['slot_bits'],p['handbits'])
        calls,fp,found,hits=map(int,cnt)
    return dict(mask=acc,state=state,backend_calls=calls,fp=fp,members_found=found,cache_hits=hits,reference_simulation_s=time.perf_counter()-timer)


def prepare(ds):
    start=time.perf_counter();kib=SETTINGS[ds];s,scores,safe=E5.load(ds)
    wl='真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部'
    spec=None if ds.endswith('_flow') else dict(E5.workload_specs(len(s.h1q)))[wl]
    base=E5.base_stream(s,wl,spec,0);n=len(base)//4;learn=base[:n];tail=base[n:]
    assert len(tail)>=Q
    old=J.RA.ra4.summarize(learn,True);lm=summarize19(learn)
    assert np.array_equal(old.keys,lm.keys) and np.array_equal(old.counts,lm.counts) and np.array_equal(old.rate,lm.rate) and old.N1==lm.N1,'GT repair affects timed input; refuse silent benchmark change'
    loaded_s=time.perf_counter()-start
    timer=time.perf_counter();cands=E5.candidates(s,scores,kib);by={(c['trees'],c['frac']):c for c in cands};g=E5.gama(cands)
    grid,_=E5.replay_best(cands,learn,s,safe);ra,info=J.ra6.select6(s,scores,lm,kib,len(tail))
    selected={'FastPLBF48':by.get((48,0.)),'Gama':g,'Gama+10%':by.get((g['trees'],.1)),'LearnGrid':grid,'RA6':ra}
    bf=[B.build(s,kib,f,K) for f in E5.FRACS];best,_=E5.replay_best(bf,learn,s,safe);selected['BF+Cache']=best
    selection_s=time.perf_counter()-timer
    archive=json.loads((WR/f'round6_bucket/results/e789/{ds}_{kib}.json').read_text())
    timer=time.perf_counter();space=J.space_of(s,ds);requests=J.mixed(base[n:n+Q],space.nm,J.POS[0],np.random.default_rng(8));request_prep_s=time.perf_counter()-timer
    exes={'NoFilter':None};details={};references={};infeasible=[]
    for name,c in selected.items():
        if c is None:infeasible.append(dict(method=name,status='infeasible',reason='Frozen model/layout does not fit24KiB budget'));continue
        timer=time.perf_counter();st=c['structure']
        if name!='BF+Cache':
            arc=archive['methods'][name]
            assert (c['trees'],c['cache_bytes'])==(arc['trees'],arc['cache_bytes']),(ds,name,'Selected configuration differs')
            assert E5.evaluate(c,tail,s,safe)['fp']==arc['tail_fp'],(ds,name,'Full tail FP differs')
            oldexe=J.Exe(s,scores,c,space)
        else:oldexe=None
        flt=Online(c,space,oldexe)
        # The compact route is tested on EVERY member and pool key, outside query timing.
        got=flt.all_probes(np.arange(len(space.h),dtype=np.int64))
        assert np.all(got[:space.nm]==1),'Native member FN'
        assert np.array_equal(got[space.nm:]==1,st.fp_static),'Compact route disagrees with frozen static flags'
        flt.reset();ref=original_reference(flt,space,requests,oldexe)
        if name!='BF+Cache':
            for variant in ('file','memory'):
                archived=archive['e8'][variant][name]
                assert ref['backend_calls']==archived['backend_calls'] and ref['members_found']==archived['members_found']
        if oldexe is None:physical=sys.getsizeof(st.data)+c['cache_bytes']
        else:
            arrays=(*oldexe.model,flt.region_cuts,st.kind,oldexe.off,oldexe.m,oldexe.k,oldexe.bits)
            assert all(a.flags.owndata for a in arrays)
            assert len({id(a) for a in arrays})==len(arrays)
            physical=sum(sys.getsizeof(a) for a in arrays)+sys.getsizeof(E5.R._MODEL_ARRAYS[s.name,c['trees']])+c['cache_bytes']
        assert physical<=st.used_bytes<=kib*1024
        flt.reset();flt.probe(int(requests[0]))
        # Compile admission with zero capacity: no speculative insert of any real request.
        feedback_absent(np.uint64(0),np.empty(0,np.uint64),np.empty(0,np.uint64),0,32,0,0,2)
        flt.reset()
        details[name]=dict(trees=c['trees'],cache_frac=c['frac'],cache_bytes=c['cache_bytes'],original_reserved_bytes=st.used_bytes,compact_online_buffer_bytes=physical,
                           model_payload_bytes=st.model_bytes,bf_payload_bytes=st.filter_bytes,static_flags_sha256=ah(st.fp_static),
                           verification_s=time.perf_counter()-timer,all_members_native_fn=0,all_pool_flags_equal=True,reference_simulation_s=ref['reference_simulation_s'],
                           expected_backend_calls=ref['backend_calls'],expected_fp=ref['fp'],expected_members_found=ref['members_found'],expected_cache_hits=ref['cache_hits'],
                           expected_mask_sha256=ah(ref['mask']),expected_cache_sha256=ah(ref['state']))
        exes[name]=flt;references[name]=ref
        print('PREPARED',ds,name,'bytes',physical,'expectedcalls',ref['backend_calls'],flush=True)
    references['NoFilter']=original_reference(None,space,requests)
    assert references['NoFilter']['members_found']==archive['e8']['file']['NoFilter']['members_found']
    return space,requests,exes,references,details,infeasible,dict(load_s=loaded_s,selection_s=selection_s,request_prepare_s=request_prep_s,gt19_statistics_equal_original=True),archive


def run(ds,output):
    freeze=check();start=time.perf_counter();kib=SETTINGS[ds]
    lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));f=lib.openblas_get_num_threads;f.restype=ctypes.c_int;assert f()==get_num_threads()==1
    space,requests,exes,refs,details,infeasible,prep,archive=prepare(ds)
    keys=space.ids.view(np.int64);expected_members=int(space.member[requests].sum())
    result=dict(status='running',dataset=ds,budget_kib=kib,freeze_sha256=freeze,queries=len(requests),member_queries=expected_members,
                request_sha256=ah(requests),request_key_sha256=ah(keys[requests]),members=space.nm,negative_pool=space.nq,
                python=platform.python_version(),sqlite=sqlite3.sqlite_version,numpy=np.__version__,numba=__import__('numba').__version__,native_threads=1,
                backend_index_payload_bytes=space.sorted_m.nbytes,backend_index_physical_bytes=sys.getsizeof(space.sorted_m),
                preparation=prep,methods=details,infeasible=infeasible,databases=[],timings=[])
    query='SELECT value FROM kv WHERE key = ?'
    with tempfile.TemporaryDirectory(prefix='sqlite_online31_') as temp:
        for variant in ('file','memory'):
            path=str(Path(temp)/'kv.sqlite') if variant=='file' else ':memory:'
            timer=time.perf_counter();con=sqlite3.connect(path)
            con.execute('CREATE TABLE kv (key INTEGER PRIMARY KEY, value BLOB NOT NULL)')
            con.executemany('INSERT INTO kv VALUES (?,?)',((int(k),b'\0'*32) for k in keys[:space.nm]));con.commit()
            assert con.execute('SELECT COUNT(*) FROM kv').fetchone()[0]==space.nm
            pages=con.execute('PRAGMA page_count').fetchone()[0];page_size=con.execute('PRAGMA page_size').fetchone()[0]
            info=dict(backend=variant,create_s=time.perf_counter()-timer,page_count=pages,page_size=page_size,database_page_bytes=pages*page_size,
                      cache_size=con.execute('PRAGMA cache_size').fetchone()[0],journal_mode=con.execute('PRAGMA journal_mode').fetchone()[0],synchronous=con.execute('PRAGMA synchronous').fetchone()[0])
            timer=time.perf_counter()
            for _ in range(2000):assert con.execute(query,(int(keys[0]),)).fetchone() is not None
            info['warmup_s']=time.perf_counter()-timer;result['databases'].append(info)
            names=list(exes)
            for rep in range(REPS):
                order=names[rep:]+names[:rep]
                for position,name in enumerate(order):
                    flt=exes[name]
                    if flt is not None:flt.reset()
                    accepted=np.zeros(len(requests),np.uint8);cursor=con.cursor()
                    # No membership labels are passed to the online driver.
                    r=online_run(cursor,query,keys,requests,flt,accepted);cursor.close();reference=refs[name]
                    assert np.array_equal(accepted,reference['mask']),(ds,name,'Backend call sequence changed')
                    for field in ('backend_calls','fp','members_found','cache_hits'):assert r[field]==reference[field],(name,field,r[field],reference[field])
                    assert r['members_found']==expected_members and r['backend_calls']==r['fp']+r['members_found']
                    if flt is not None:
                        assert np.array_equal(flt.data,reference['state']),(ds,name,'Final packed cache differs')
                        p=flt.spec;assert K.count_member_hits(flt.data,space.sorted_m,p['buckets'],40,p['Q'],p['ob'],p['slot_bits'],4)==0
                    row=dict(backend=variant,rep=rep,order_position=position,method=name,**r,accepted_mask_sha256=ah(accepted),
                             final_cache_sha256=ah(flt.data) if flt is not None else None,full_mask_equal_reference=True,packed_cache_equal_reference=True,member_fn=0)
                    result['timings'].append(row);save(output,result)
                    print(f'TIMED {ds} {variant} rep={rep} {name}: {r["ns_per_query"]/1000:.3f}us calls={r["backend_calls"]} FP={r["fp"]}',flush=True)
            con.close()
    assert len(result['timings'])==len(exes)*2*REPS
    result.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    check();save(output,result);print('COMPLETE',ds,len(result['timings']),'timings',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=SETTINGS);p.add_argument('output',type=Path);a=p.parse_args();assert not a.output.exists()
    try:run(a.dataset,a.output)
    except Exception as e:save(a.output.with_suffix('.error.json'),dict(status='failed',error=repr(e)));raise

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(WR/'round34_backend_cost/src'))
from client35 import RpcFilter,online_rpc,admit_from_prefix,np,K
from rpc35 import Client
from worker34 import prepare_fixed
from cost34 import SETTINGS,sha,ah,save
from worker31 import original_reference
import json,time,os,subprocess,tempfile,selectors,resource,ctypes,shutil
from numba import get_num_threads
METHODS=('NoFilter','BF+Cache','RA6')


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in f['sources'].items():assert sha(BLOOM/rel)==h,rel
    return sha(ROOT/'plan/freeze.json')


def start_server(ds,database,err):
    proc=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src/backend35.py'),ds,str(database)],cwd=BLOOM,stdout=subprocess.PIPE,stderr=err,text=True)
    selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
    try:
        if not selector.select(300):raise TimeoutError('Backend startup exceeded300s')
        line=proc.stdout.readline()
        if not line:raise RuntimeError('Backend exited before readiness; see server log')
        ready=json.loads(line)
        assert ready['event']=='ready' and ready['host']=='127.0.0.1' and ready['pid']==proc.pid and proc.pid!=os.getpid()
        return proc,ready,line
    except BaseException:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        raise
    finally:selector.close()


def run(ds,out,pilot=False):
    frozen=check();start=time.perf_counter();lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));getter=lib.openblas_get_num_threads;getter.restype=ctypes.c_int;assert getter()==get_num_threads()==1
    space,full_requests,keys,prepared,fullrefs,prior,prep=prepare_fixed(ds)
    requests=full_requests[:2000].copy() if pilot else full_requests
    filters={'NoFilter':None,**{m:RpcFilter(prepared[m]) for m in ('BF+Cache','RA6')}}
    references={}
    for method in METHODS:
        if method=='NoFilter':references[method]=original_reference(None,space,requests)
        elif not pilot:references[method]=fullrefs[method]
        else:
            # Independent known-label reference only; never passed into the online RPC function.
            previous=prepared[method]
            # Rebuild the reference using verified static flags and EVERY CLOCK lookup.
            flags=np.concatenate([np.ones(space.nm,np.bool_),previous.c['structure'].fp_static])
            from reference35 import reference_mixed
            state=previous.data.copy();state.fill(0)
            if len(state)>1:state[1]=previous.spec['buckets'];state[2]=previous.spec['slots']
            cnt,mask=reference_mixed(requests,space.h,space.member,flags,state,space.sorted_m,previous.spec['buckets'],previous.spec['Q'],previous.spec['ob'],previous.spec['slot_bits'],previous.spec['handbits'])
            references[method]=dict(mask=mask,state=state,backend_calls=int(cnt[0]),fp=int(cnt[1]),members_found=int(cnt[2]),cache_hits=int(cnt[3]))
    del prepared,fullrefs
    # Prime scalar transport-facing cache insertion without inserting any actual query.
    admit_from_prefix(np.empty(0,np.uint64),np.uint64(0),1,0,32,0,0,2)
    for flt in filters.values():
        if flt is not None:flt.probe(int(requests[0]));flt.reset();assert not hasattr(flt,'sorted_members') and not hasattr(flt,'space')
    result=dict(status='running',dataset=ds,budget_kib=SETTINGS[ds],pilot=pilot,queries=len(requests),full_request_sha256=ah(full_requests),request_sha256=ah(requests),
                member_queries=references['NoFilter']['members_found'],members=space.nm,freeze_sha256=frozen,native_threads=1,preparation=prep,
                client_index_usage='Verification harness only; online filter has no member index; actual prefix computed on server after SQL absence',
                configurations={m:prior['methods'][m] for m in ('RA6','BF+Cache')},timings=[])
    reps=1 if pilot else 3;proc=None;rpc=None;stdout=''
    server_log=out.with_name(out.stem+'_server.log');assert not server_log.exists()
    with tempfile.TemporaryDirectory(prefix='sqlite_tcp35_') as temp,server_log.open('x') as err:
        if shutil.disk_usage(temp).free<1024**3:raise RuntimeError('At least1GiB free temporary storage required')
        try:
            proc,ready,line=start_server(ds,Path(temp)/'kv.sqlite',err);stdout+=line
            assert ready['members']==space.nm and ready['index_payload_bytes']==8*space.nm and ready['native_threads']==1
            db31=next(r for r in prior['databases'] if r['backend']=='file')
            assert (ready['page_count'],ready['page_size'])==(db31['page_count'],db31['page_size'])
            result['backend']=ready;rpc=Client('127.0.0.1',ready['port']);rpc.ping()
            total_calls=0
            for rep in range(reps):
                order=METHODS[rep:]+METHODS[:rep]
                for position,method in enumerate(order):
                    flt=filters[method]
                    if flt is not None:flt.reset()
                    mask=np.zeros(len(requests),np.uint8);rpc.reset()
                    r=online_rpc(rpc,keys,requests,flt,mask)
                    server=rpc.stats();ref=references[method];total_calls+=r['backend_calls']
                    assert np.array_equal(mask,ref['mask'])
                    for field in ('backend_calls','fp','members_found','cache_hits'):assert r[field]==ref[field],(method,field)
                    assert r['members_found']==result['member_queries'] and r['received_value_bytes']==r['members_found']*32
                    assert r['backend_calls']==rpc.sql_calls==server['sql_calls'] and server['total_sql_calls']==total_calls
                    assert server['found']==r['members_found'] and server['absent']==r['fp']
                    assert server['prefix_queries']==(r['fp'] if r['need_backend_prefix'] else 0)
                    assert r['query_sent_bytes']==r['backend_calls']*9 and r['query_received_bytes']==r['backend_calls']*8+r['members_found']*32
                    if flt is not None:
                        assert np.array_equal(flt.data,ref['state'])
                        p=flt.spec;assert K.count_member_hits(flt.data,space.sorted_m,p['buckets'],40,p['Q'],p['ob'],p['slot_bits'],4)==0
                    row=dict(rep=rep,method=method,order_position=position,**r,server_statistics=server,
                             accepted_mask_sha256=ah(mask),cache_sha256=ah(flt.data) if flt is not None else None,query_mask_equal=True,cache_bytes_equal=True,member_fn=0)
                    result['timings'].append(row);save(out,result)
                    print(f'TCP {ds} pilot={pilot} rep={rep} {method}: {r["ns_per_query"]/1000:.3f}us/query SQL={r["backend_calls"]} FP={r["fp"]} server_prefix={server["prefix_queries"]}',flush=True)
            rpc.shutdown();rpc.close();rpc=None;proc.wait(timeout=15);stdout+=proc.stdout.read();assert proc.returncode==0
        finally:
            if rpc is not None:
                try:rpc.shutdown()
                except Exception:pass
                rpc.close()
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
            if proc is not None and proc.stdout is not None:proc.stdout.close()
            if stdout:out.with_name(out.stem+'_server_stdout.log').write_text(stdout)
    assert len(result['timings'])==3*reps;check()
    result.update(status='complete',wall_s=time.perf_counter()-start,client_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save(out,result);print('COMPLETE',ds,'pilot' if pilot else 'formal',len(result['timings']),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=SETTINGS);p.add_argument('output',type=Path);p.add_argument('--pilot',action='store_true');a=p.parse_args();assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True)
    try:run(a.dataset,a.output,a.pilot)
    except Exception as e:save(a.output.with_suffix('.error.json'),dict(status='failed',error=repr(e),pilot=a.pilot));raise

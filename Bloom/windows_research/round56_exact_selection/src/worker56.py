"""One fresh serial worker: full method warmup, one timed selection, strict round55 regression."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common56 import *
from selection56 import select


def run(ds,kib,method,rep,pilot=False):
    start=time.perf_counter();start_epoch=time.time();freeze_check()
    p,oldcase=reference(ds,kib);old=next(r for r in oldcase['rows'] if r['method']==method)
    d=C.load(ds);w=oldcase['case']['workload']
    spec=dict(C.E5.workload_specs(len(d.s.h1q)))[w] if not ds.endswith('_flow') else None
    t=time.perf_counter();base=C.E5.base_stream(d.s,w,spec,0,10000000);n=len(base)//4;learn,tail=base[:n],base[n:]
    stream_s=time.perf_counter()-t
    assert C.ah(learn)==oldcase['learning_sha'] and C.ah(tail)==oldcase['base_tail_sha']
    with C.scope(d.cache):
        t=time.perf_counter();c,meta,aux=select(d,method,kib,learn,len(tail))
        warm_choice=dict(trees=c['trees'],frac=c['frac'],flags_sha=C.ah(c['structure'].fp_static))
        del c,meta,aux;gc.collect();warmup_s=time.perf_counter()-t
        c,meta,aux=select(d,method,kib,learn,len(tail))
        assert warm_choice==dict(trees=c['trees'],frac=c['frac'],flags_sha=C.ah(c['structure'].fp_static))
        t=time.perf_counter();evalout=C.evaluate(d,c,tail)
        row=dict(trees=c['trees'],frac=c['frac'],flags_sha=C.ah(c['structure'].fp_static),**C.ledger(c),**evalout)
        check_regression(row,old);verification_s=time.perf_counter()-t
        # State measures are deliberately disaggregated, not called total deployment memory.
        state=dict(learning_trace_view_payload_bytes=int(learn.nbytes),full_driver_trace_owner=owner_bytes(learn),
                   learning_trace_compact_copy_physical_bytes=int(learn.nbytes)+sys.getsizeof(np.empty(0,np.int64)),
                   raw_key_blob_physical_bytes=sys.getsizeof(d.blob),raw_key_offsets_physical_bytes=sys.getsizeof(d.off),
                   member_index_required_bytes=0,trace_owner_note='Driver holds full stream; compact copy bytes are a hypothetical standalone learning representation, not current RSS')
        del c,aux
    freeze_check()
    result=dict(status='complete',dataset=ds,budget_kib=kib,workload=w,seed=0,method=method,rep=rep,pilot=pilot,
                reference_file=str(p.relative_to(BLOOM)),reference_sha256=sha(p),learning_sha=oldcase['learning_sha'],base_tail_sha=oldcase['base_tail_sha'],
                learning_queries=n,tail_queries=len(tail),input_prepare=d.meta,stream_generation_s=stream_s,warmup_s=warmup_s,
                selection=meta,verification_s=verification_s,selected=row,state=state,
                peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                worker_s=time.perf_counter()-start,elapsed_epoch_s=time.time()-start_epoch,
                native_threads={v:os.environ[v] for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS')},
                regression55=True,timing_scope='Serial fresh-process, warmed full-pool round55 implementation; selection includes learning preprocessing and candidate construction, excludes shared input/model preparation and post-selection tail verification')
    assert result['peak_rss_bytes']<8*1024**3
    name=f'{ds}_{kib}_rep{rep}_{method}.json'
    save(ROOT/('results/pilot' if pilot else 'results/main')/name,result)
    print('SELECTION_COMPLETE',name,'seconds',meta['selection_s'],flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('kib',type=int);p.add_argument('method',choices=METHODS);p.add_argument('rep',type=int,choices=range(REPS));p.add_argument('--pilot',action='store_true')
    a=p.parse_args();run(a.dataset,a.kib,a.method,a.rep,a.pilot)

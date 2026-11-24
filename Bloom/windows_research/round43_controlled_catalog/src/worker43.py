import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from catalog43 import *
from online43 import measure,database,SQL_METHODS
import tempfile,resource,shutil


def run(strength,seed,pilot=False):
    frozen=check();name='pilot' if pilot else f'a{strength}_s{seed}';dest=ROOT/f'results/{name}.json';assert not dest.exists();started=time.perf_counter()
    if not pilot:assert json.loads((ROOT/'results/pilot_gate.json').read_text())['passed']
    assert shutil.disk_usage(ROOT).free>=2*1024**3
    t=time.perf_counter();s,X,hashes,meta=catalogue(strength,seed);generation_s=time.perf_counter()-t
    scores,training=train(s,X,seed)
    t=time.perf_counter();keys=[int(x).to_bytes(8,'little') for x in s.ids];encoding_s=time.perf_counter()-t
    input_path=None
    if not pilot:
        input_path=ROOT/f'cache/{name}.npz';assert not input_path.exists();input_path.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(input_path,ids=s.ids,y=s.y,X=X,member_train=s.split['member_train'],neg_train=s.split['neg_train'],neg_val=s.split['neg_val'],neg_test=s.split['neg_test'])
    with exact64():
        t=time.perf_counter();warm=B.build(s,16,.1,F);evaluate(warm,np.array([0,1],np.int64),s);E5.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.);jit_s=time.perf_counter()-t
        out=dict(status='running',pilot=pilot,strength=strength,seed=seed,freeze_sha256=frozen,catalogue=meta,generation_s=generation_s,training=training,key_encoding_s=encoding_s,JIT_warm_s=jit_s,local_generated_input_sha256=W.sha(input_path) if input_path else None,arrays=dict(key_payload_bytes=s.ids.nbytes,feature_payload_bytes=X.nbytes,feature_owning_bytes=sys.getsizeof(X),input_raw_keys_python_bytes=sys.getsizeof(keys)+sum(sys.getsizeof(k) for k in keys)),cases=[])
        with tempfile.TemporaryDirectory(prefix='catalogue43_') as tmp:
            con,db=database(Path(tmp)/'kv.sqlite',keys,s.y);out['database']=db
            try:
                for association in (('neutral',) if pilot else ASSOCIATIONS):
                    t=time.perf_counter();learn,tail,stream_meta=stream(s,association,seed);stream_s=time.perf_counter()-t
                    t=time.perf_counter();lm=W.summarize19(learn);summary_s=time.perf_counter()-t
                    if not pilot:
                        sp=ROOT/f'cache/{name}_{association}.npz';assert not sp.exists();np.savez_compressed(sp,learn=learn,tail=tail);stream_meta['local_stream_file_sha256']=W.sha(sp)
                    bins=(s.q_ids>>np.uint64(56)).astype(np.int64);present=np.zeros(256,np.bool_);present[(s.ids[s.y]>>np.uint64(56)).astype(np.int64)]=True
                    support_fp=int(present[bins[tail]].sum())
                    for kib in ((16,) if pilot else BUDGETS):
                        cs,times,info=select_all(s,scores,learn,lm,kib,len(tail));rows=[]
                        for method,c in cs.items():
                            r,_=evaluate(c,tail,s)
                            rows.append(dict(method=method,**r,**ledger(c),selection_build_s=times[method],learning_summary_charged_s=summary_s if method in ('RA6','RA-global','ZGate') else 0,static_flags_sha256=W.ah(c['structure'].fp_static)))
                        fixed=controls(s,scores,lm,len(tail),kib,tail)
                        timed,tprep=measure(cs,s,scores,hashes,keys,tail,seed,con.cursor(),n=2000 if pilot else 20000,reps=1 if pilot else 3)
                        case=dict(association=association,budget_kib=kib,learning_queries=len(learn),tail_queries=len(tail),stream=stream_meta,stream_generation_s=stream_s,GT_summary_s=summary_s,feature_support_baseline=dict(fp=support_fp,member_fn=0,lookup_table_bytes=sys.getsizeof(present),note='Only rejects feature bins with no members; exact keys still verified by backend'),selection=info,rows=rows,controls=fixed,query_preparation=tprep,timings=timed)
                        out['cases'].append(case);W.save(dest,out)
                        counts={r['method']:r['fp'] for r in rows};print('CASE',strength,seed,association,kib,counts,flush=True)
            finally:con.close()
    assert len(out['cases'])==(1 if pilot else 9) and E5.K is K_ORIGINAL;check()
    out.update(status='complete',wall_s=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);W.save(dest,out)
    print('WORKER_COMPLETE',name,out['wall_s'],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('strength',type=int,choices=STRENGTHS);p.add_argument('seed',type=int,choices=SEEDS);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    try:run(a.strength,a.seed,a.pilot)
    except Exception as e:W.save(ROOT/f'results/{"pilot" if a.pilot else "a"+str(a.strength)+"_s"+str(a.seed)}.failure.json',dict(status='failed',error=repr(e)));raise

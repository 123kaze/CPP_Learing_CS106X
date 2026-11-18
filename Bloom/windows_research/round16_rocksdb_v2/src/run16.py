"""Serial, failure-propagating database experiment; do not retry incomplete results."""
from common16 import *
import subprocess
import time
import platform


def check(r):
    assert r['status']=='ok' and r['exit_code']==0
    assert r['queries']==TAIL+POS and r['positive_queries']==POS and r['negative_queries']==TAIL
    assert r['wrong_answers']==r['invalid_values']==r['member_fn_after_run']==0
    assert r['db_calls']==r['returned_members']+r['db_negative_misses']
    assert r['rocksdb_statistics_delta']['rocksdb.number.keys.read']==r['db_calls']
    assert r['block_cache_capacity']==CACHES[r['cache_regime']]
    effective=r['configuration_check']
    assert effective['effective_cache_capacity']==CACHES[r['cache_regime']] and effective['cache_object_equals_db_usage']
    assert effective['explicit_default_column_family'] and effective['bloom_useful_of_2000_misses']>=1900


def run_job(cmd,out):
    log=out.with_suffix('.log')
    assert not log.exists(),f'Partial log exists, no automatic retry: {log}'
    start=time.perf_counter()
    with log.open('x') as f:proc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    elapsed=time.perf_counter()-start
    r=json.loads(out.read_text()) if out.exists() else dict(status='error',error=f'worker exit {proc.returncode}')
    r.update(exit_code=proc.returncode,process_wall_s=elapsed);save(out,r)
    if proc.returncode or r['status'] not in ('ok','complete'):
        print(f'FAILED {out.name}: exit={proc.returncode}\n'+log.read_text()[-4000:],flush=True)
        raise SystemExit(1)
    return r


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','cache_inputs','dependency'):
        for rel,h in freeze[section].items():assert digest(BLOOM/rel)==h,(section,rel)
    database=json.loads((ROOT/'results/database.json').read_text());assert database['status']=='complete'
    for rel,h in {**database['inputs_sha256'],**database['sst_sha256']}.items():assert digest(ROOT/rel)==h,rel
    manifest=dict(freeze=freeze,database=database,methods=METHODS,workloads=WORKLOADS,block_caches=CACHES,
                  reps=REPS,python=sys.version,platform=platform.platform(),rocksdict='0.3.29',rocksdb='9.8.4')
    mp=ROOT/'results/manifest.json'
    if mp.exists():assert json.loads(mp.read_text())==json.loads(json.dumps(manifest))
    else:save(mp,manifest)
    for rep in range(REPS):
        out=ROOT/f'results/filters_rep{rep}.json'
        if out.exists():
            r=json.loads(out.read_text());assert r['status']=='complete' and r['exit_code']==0
        else:
            print(f'START fresh training/selection rep{rep}',flush=True)
            r=run_job([sys.executable,'-u',str(ROOT/'src/build16.py'),'--rep',str(rep)],out)
            print(f'COMPLETE construction rep{rep}: {r["process_wall_s"]:.1f}s',flush=True)
        assert len(r['methods'])==8
    dest=ROOT/'results/main';dest.mkdir(exist_ok=True)
    records=[]
    for wi,workload in enumerate(WORKLOADS):
        for ci,cache in enumerate(CACHES):
            for rep in range(REPS):
                shift=(rep+wi*2+ci)%len(METHODS)
                order=METHODS[shift:]+METHODS[:shift]
                for method in order:
                    out=dest/f'{workload}_{cache}_rep{rep}_{method}.json'
                    if out.exists():
                        r=json.loads(out.read_text());check(r)
                    else:
                        print(f'START {out.stem}',flush=True)
                        cmd=[sys.executable,'-u',str(ROOT/'src/query16.py'),'--method',method,'--workload',workload,
                             '--cache',cache,'--rep',str(rep),'--output',str(out)]
                        r=run_job(cmd,out);check(r)
                        print(f'COMPLETE {out.stem}: {r["seconds"]:.3f}s Get={r["db_calls"]} data-hit={r["data_block_hit_rate"]:.3f}',flush=True)
                    records.append(out.name)
                save(dest/'progress.json',dict(completed=len(records),expected=60,files=records))
    assert len(records)==len(list(dest.glob('*_rep*_*.json')))==60
    for workload in WORKLOADS:
        for method in METHODS:
            rr=[json.loads((dest/f'{workload}_{cache}_rep{rep}_{method}.json').read_text()) for cache in CACHES for rep in range(REPS)]
            for r in rr[1:]:
                for key in ('db_calls','db_negative_misses','cache_hits','filter_rejections','cache_insertions','stream_sha256'):
                    assert r[key]==rr[0][key],(workload,method,key)
    for rel,h in database['sst_sha256'].items():assert digest(ROOT/rel)==h,'Immutable SST changed'
    save(dest/'completion.json',dict(status='complete',query_processes=60,construction_processes=3,
                                    methods=5,workloads=2,cache_regimes=2,reps=3,manifest_sha256=digest(mp)))
    print('ROUND16 COMPLETE: 60 real-Get runs, 3 fresh training/selection repetitions, all answers verified',flush=True)


if __name__=='__main__':main()

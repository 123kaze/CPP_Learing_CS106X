"""Exact-equivalence campaign followed by optimized full-grid timing controls."""
from common21 import *
import json
import subprocess
import time
import platform


def job(script,args,out):
    if out.exists():
        row=json.loads(out.read_text())
        assert row['status']=='ok' and row.get('exit_code')==0 and 'process_wall_s' in row,('Failed or partial result',out)
        return row
    log=out.with_suffix('.log');assert not log.exists(),('Partial log, no automatic retry',log)
    print('START',out.stem,flush=True);start=time.perf_counter()
    with log.open('x') as f:p=subprocess.run([sys.executable,'-u',str(ROOT/'src'/script),*args,'--output',str(out)],stdout=f,stderr=subprocess.STDOUT)
    row=json.loads(out.read_text()) if out.exists() else dict(status='error',error=f'worker exit {p.returncode}')
    row.update(exit_code=p.returncode,process_wall_s=time.perf_counter()-start);save(out,row)
    if p.returncode or row['status']!='ok':
        print('FAILED',out.name,'\n'+log.read_text()[-5000:],flush=True);raise SystemExit(1)
    print('COMPLETE',out.stem,f'{row["process_wall_s"]:.1f}s',flush=True)
    return row


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for kind in ('sources','inputs'):
        for rel,h in freeze[kind].items():assert digest(BLOOM/rel)==h,(kind,rel)
    manifest=dict(freeze=freeze,datasets=DATASETS,cases={ds:cases(ds) for ds in DATASETS},
                  timing_reps=TIMING_REPS,python=sys.version,platform=platform.platform())
    path=ROOT/'results/manifest.json'
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(manifest))
    else:save(path,manifest)
    for mode in ('index','fp64'):
        p=ROOT/f'results/pilot_{mode}.json';row=json.loads(p.read_text())
        assert row['status']=='ok' and row['pilot'] and len(row['cases'])==1
        c=row['cases'][0]
        assert c['verification']['all_counters_bit_exact'] and c['verification']['all_states_bit_exact']
    main_dir=ROOT/'results/main';main_dir.mkdir(exist_ok=True)
    completed=0;timed=0
    for ds in DATASETS:
        for mode in ('index','fp64'):
            r=job('worker21.py',['--dataset',ds,'--cache',mode],main_dir/f'{ds}_{mode}.json')
            assert r['dataset']==ds and r['cache']==mode and not r['pilot']
            assert len(r['cases'])==len(cases(ds))
            assert {(c['budget_kib'],c['workload'],c['seed'],c['cohort']) for c in r['cases']}==set(cases(ds))
            for c in r['cases']:
                assert c['verification']['all_counters_bit_exact'] and c['verification']['all_states_bit_exact']
                assert c['same_round20_choice'] and c['same_round20_fp']
                expected=TIMING_REPS if timed_case(ds,c['budget_kib'],c['workload'],c['seed']) else 0
                assert len(c['timing'])==expected
                timed+=bool(expected)
            completed+=len(r['cases'])
            save(ROOT/'results/progress.json',dict(completed_cases=completed,expected_cases=192,timed_gate_settings=timed))
    assert completed==192 and timed==16
    grid_dir=ROOT/'results/grid';grid_dir.mkdir(exist_ok=True)
    for ds in ('url','caida'):
        for mode in ('index','fp64'):
            r=job('grid21.py',['--dataset',ds,'--cache',mode],grid_dir/f'{ds}_{mode}.json')
            assert r['all_counter_pairs_exact'] and r['all_packed_state_pairs_exact'] and len(r['timing'])==TIMING_REPS
    for rel,h in freeze['sources'].items():assert digest(BLOOM/rel)==h
    save(ROOT/'results/completion.json',dict(status='complete',cases=192,candidate_state_pairs=2688,
         gate_timing_settings=16,grid_timing_settings=4,repetitions=3,manifest_sha256=digest(path)))
    print('ROUND21 COMPLETE:192 exact cases,16 gate timing settings,4 optimized-grid controls',flush=True)


if __name__=='__main__':main()

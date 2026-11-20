"""192 cases x5 selectors x3 fresh selection rebuilds, serial single-threaded."""
from common_v2 import *
import subprocess
import time
import json
import platform


def validate(r,ds,mode):
    assert r['status']=='ok' and r['exit_code']==0 and not r['pilot']
    assert (r['dataset'],r['cache'])==(ds,mode)
    assert len(r['cases'])==len(cases(ds))
    assert {(c['budget_kib'],c['workload'],c['seed'],c['cohort']) for c in r['cases']}==set(cases(ds))
    for c in r['cases']:
        assert len(c['timing'])==15
        assert {(t['rep'],t['method']) for t in c['timing']}=={(rep,m) for rep in range(REPS) for m in METHODS}
        assert c['guard_verification']['candidates']==14
        for t in c['timing']:
            assert t['selection_s']>0 and all(t[k]>=0 for k in ('statistics_s','anchor_select_build_s','candidate_build_s','route_s','replay_s'))
            if t['method'].endswith('shared'):assert t['all_counters_exact'] and t['all_cache_bytes_exact']


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for kind in ('sources','inputs'):
        for rel,h in freeze[kind].items():assert digest(BLOOM/rel)==h,(kind,rel)
    manifest=dict(freeze=freeze,methods=METHODS,reps=REPS,cases={ds:cases(ds) for ds in DATASETS},
                  python=sys.version,platform=platform.platform())
    path=ROOT/'results/manifest.json'
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(manifest))
    else:save(path,manifest)
    for mode in ('index','fp64'):
        p=json.loads((ROOT/f'results/pilot_{mode}.json').read_text());assert p['status']=='ok' and p['pilot']
        assert len(p['cases'])==1 and len(p['cases'][0]['timing'])==15
    dest=ROOT/'results/main';dest.mkdir(exist_ok=True);n=0
    for ds in DATASETS:
        for mode in ('index','fp64'):
            out=dest/f'{ds}_{mode}.json'
            if out.exists():r=json.loads(out.read_text());validate(r,ds,mode)
            else:
                log=out.with_suffix('.log');assert not log.exists(),('Partial log, no auto-retry',log)
                print(f'START {ds} {mode}: {len(cases(ds))} cases x15 complete selection timings',flush=True)
                start=time.perf_counter()
                with log.open('x') as f:
                    proc=subprocess.run([sys.executable,'-u',str(ROOT/'src/worker_v2.py'),'--dataset',ds,'--cache',mode,'--output',str(out)],stdout=f,stderr=subprocess.STDOUT)
                r=json.loads(out.read_text()) if out.exists() else dict(status='error',error=f'exit {proc.returncode}')
                r.update(exit_code=proc.returncode,process_wall_s=time.perf_counter()-start);save(out,r)
                if proc.returncode or r['status']!='ok':
                    print(f'FAILED {out.name}\n'+log.read_text()[-5000:],flush=True);raise SystemExit(1)
                validate(r,ds,mode)
            n+=len(r['cases'])
            save(ROOT/'results/progress.json',dict(cases_complete=n,cases_expected=192,timings_complete=n*15,timings_expected=2880))
            print(f'COMPLETE {ds} {mode}: {n}/192 cases, {n*15}/2880 timings',flush=True)
    assert n==192
    for rel,h in freeze['sources'].items():assert digest(BLOOM/rel)==h
    save(ROOT/'results/completion.json',dict(status='complete',jobs=16,cases=192,methods=5,reps=3,
        selection_timings=2880,manifest_sha256=digest(path)))
    print('ROUND21 V2 COMPLETE:192 cases,2880 full selection timings, unchanged outcomes and exact cache states',flush=True)


if __name__=='__main__':main()

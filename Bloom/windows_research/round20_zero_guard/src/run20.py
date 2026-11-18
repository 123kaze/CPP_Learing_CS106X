"""Serial complete matrix with no failed/partial-run automatic retry."""
from common20 import *
import subprocess
import time
import json
import platform


def check(r,ds,mode,pilot=False):
    assert r['status']=='ok' and r['exit_code']==0
    assert (r['dataset'],r['cache'],r['pilot'])==(ds,mode,pilot)
    expected=cases(ds)[:1] if pilot else cases(ds)
    assert len(r['cases'])==len(expected)
    assert {(c['budget_kib'],c['workload'],c['seed'],c['cohort']) for c in r['cases']}==set(expected)
    for c in r['cases']:
        g=c['gate'];assert g['empirical_nonregression']
        assert g['selected_learning_fp']==min(g['zero_learning_fp'],g['anchor_learning_fp'])
        assert (g['family']=='zero')==(g['zero_learning_fp']<=g['anchor_learning_fp'])
        assert set(c['methods'])==set(METHODS)
        assert c['methods']['RA6-ZGate']['trees']==0 if g['family']=='zero' else c['methods']['RA6-ZGate']['trees']>0


def job(ds,mode,pilot=False):
    folder=ROOT/'results'/('pilot' if pilot else 'main');folder.mkdir(exist_ok=True)
    out=folder/f'{ds}_{mode}.json'
    if out.exists():
        r=json.loads(out.read_text());check(r,ds,mode,pilot);return r
    log=out.with_suffix('.log');assert not log.exists(),f'Partial log: {log}'
    cmd=[sys.executable,'-u',str(ROOT/'src/worker20.py'),'--dataset',ds,'--cache',mode,'--output',str(out)]
    if pilot:cmd.append('--pilot')
    print('START',folder.name,ds,mode,flush=True);t=time.perf_counter()
    with log.open('x') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    r=json.loads(out.read_text()) if out.exists() else dict(status='error',error=f'worker exit {p.returncode}')
    r.update(exit_code=p.returncode,process_wall_s=time.perf_counter()-t);save(out,r)
    if p.returncode or r['status']!='ok':
        print('FAILED',out.name,'\n',log.read_text()[-4000:],flush=True);raise SystemExit(1)
    check(r,ds,mode,pilot);print('COMPLETE',folder.name,ds,mode,len(r['cases']),flush=True)
    return r


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for rel,h in freeze[group].items():assert digest(BLOOM/rel)==h,(group,rel)
    manifest=dict(freeze=freeze,methods=METHODS,cases={ds:cases(ds) for ds in DATASETS},python=sys.version,platform=platform.platform())
    path=ROOT/'results/manifest.json'
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(manifest))
    else:save(path,manifest)
    for mode in ('index','fp64'):
        p=job('caida_tcp_flow',mode,True);assert p['pilot_exhaustive_learning_check']
    total=0
    for ds in DATASETS:
        for mode in ('index','fp64'):
            total+=len(job(ds,mode)['cases'])
            save(ROOT/'results/progress.json',dict(completed_cases=total,expected_cases=192))
    assert total==192
    for rel,h in freeze['sources'].items():assert digest(BLOOM/rel)==h
    save(ROOT/'results/completion.json',dict(status='complete',jobs=16,cases=192,live_method_rows=576,
            learning_nonregression_cases=192,manifest_sha256=digest(path)))
    print('ROUND20 COMPLETE:192 cases, empirical learning non-regression verified; tail outcomes retained',flush=True)


if __name__=='__main__':main()

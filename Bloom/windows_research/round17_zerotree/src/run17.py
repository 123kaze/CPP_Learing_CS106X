"""Serial 192-case comparison, each cache format isolated in its own process."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[v]='1'
from common17 import *
import sys
import subprocess
import time
import platform


def checked(row,ds,mode):
    assert row['status']=='ok' and row['exit_code']==0 and not row['pilot']
    assert (row['dataset'],row['cache'])==(ds,mode)
    expected=set(cases(ds))
    assert len(row['results'])==len(expected)
    assert {(r['budget_kib'],r['workload'],r['seed'],r['cohort']) for r in row['results']}==expected
    for r in row['results']:
        assert set(r['methods'])==set(METHODS)
        assert r['zero_info']['built']==5 and r['zero_info']['zero_candidates']==13
        for m,v in r['methods'].items():
            assert v['member_checks_passed'] and v['total_bytes']<=r['budget_kib']*1024
            if v['trees']==0:assert v['model_bytes']==0 and v['native_zero_checks']


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for rel,h in freeze[group].items():assert digest(BLOOM/rel)==h,(group,rel)
    for mode in ('index','fp64'):
        pilot=json.loads((ROOT/f'results/pilot_{mode}.json').read_text())
        assert pilot['status']=='ok' and pilot['disabled_zero_reproduces_frozen_ra6']
    manifest=dict(freeze=freeze,methods=METHODS,datasets=DATASETS,expected_cases=sum(len(cases(ds)) for ds in DATASETS)*2,
                  cases={ds:cases(ds) for ds in DATASETS},python=sys.version,platform=platform.platform())
    assert manifest['expected_cases']==192
    path=ROOT/'results/manifest.json'
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(manifest))
    else:save(path,manifest)
    dest=ROOT/'results/main';dest.mkdir(exist_ok=True);completed=0
    for ds in DATASETS:
        for mode in ('index','fp64'):
            out=dest/f'{ds}_{mode}.json'
            if out.exists():
                row=json.loads(out.read_text());checked(row,ds,mode)
            else:
                log=out.with_suffix('.log');assert not log.exists(),f'Partial log exists: {log}'
                start=time.perf_counter();print(f'START {ds} {mode}: {len(cases(ds))} cases',flush=True)
                with log.open('x') as f:
                    proc=subprocess.run([sys.executable,'-u',str(ROOT/'src/worker17.py'),'--dataset',ds,'--cache',mode,'--output',str(out)],stdout=f,stderr=subprocess.STDOUT)
                row=json.loads(out.read_text()) if out.exists() else dict(status='error',error=f'worker exit {proc.returncode}')
                row.update(exit_code=proc.returncode,process_wall_s=time.perf_counter()-start);save(out,row)
                if proc.returncode or row['status']!='ok':
                    print(f'FAILED {out.name}\n'+log.read_text()[-4000:],flush=True);raise SystemExit(1)
                checked(row,ds,mode)
            completed+=len(row['results'])
            print(f'COMPLETE {ds} {mode}; cases={completed}/192',flush=True)
            save(dest/'progress.json',dict(completed_cases=completed,expected_cases=192))
    assert completed==192 and len(list(dest.glob('*_index.json')))+len(list(dest.glob('*_fp64.json')))==16
    save(dest/'completion.json',dict(status='complete',jobs=16,cases=192,method_rows=1536,
                                    manifest_sha256=digest(path)))
    print('ROUND17 COMPLETE: 192 cases, 1536 method rows, zero-tree native and old-result regressions passed',flush=True)


if __name__=='__main__':main()

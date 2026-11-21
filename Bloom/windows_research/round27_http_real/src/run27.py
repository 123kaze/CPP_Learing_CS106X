"""Sequential fresh workers; never overwrite or automatically resume partial results."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from data27 import save,sha
import subprocess
import json
import time


def freeze():
    import worker27
    p=ROOT/'plan/freeze.json';assert not p.exists(),'Frozen protocol already exists'
    paths=set((ROOT/'src').glob('*.py'))|{ROOT/'plan/design-freeze.md'}
    for mod in tuple(sys.modules.values()):
        value=getattr(mod,'__file__',None)
        if not value:continue
        q=Path(value).resolve()
        if q.is_relative_to(BLOOM) and not q.is_relative_to(BLOOM/'.condaenv') and q.suffix=='.py':paths.add(q)
    save(p,dict(created='2026-11-21',sources={str(q.relative_to(BLOOM)):sha(q) for q in sorted(paths)},
                inputs={str(q.relative_to(BLOOM)):sha(q) for q in sorted((ROOT/'cache').glob('*.npz'))},
                budgets_kib=worker27.BUDGETS,seeds=worker27.SEEDS,trees=worker27.E5.TREES,cache_fracs=worker27.E5.FRACS))
    print('FROZEN',len(paths),'sources',flush=True)


def run():
    manifest=json.loads((ROOT/'plan/freeze.json').read_text());out=ROOT/'results';out.mkdir(exist_ok=True)
    assert not (out/'completion.json').exists()
    for p,h in manifest['inputs'].items():assert sha(BLOOM/p)==h
    jobs=[];start=time.perf_counter()
    for ds in ('nasa_jul95','nasa_aug95'):
        for seed in manifest['seeds']:
            dest=out/f'{ds}_{seed}.json';log=dest.with_suffix('.log');assert not dest.exists() and not log.exists()
            with log.open('x') as f:r=subprocess.run([sys.executable,'-I',str(ROOT/'src/worker27.py'),str(ROOT/f'cache/{ds}.npz'),str(seed),str(dest)],stdout=f,stderr=subprocess.STDOUT,cwd=BLOOM)
            jobs.append(dict(dataset=ds,seed=seed,exit_code=r.returncode,log=log.name))
            save(out/'progress.json',dict(status='running' if r.returncode==0 else 'failed',jobs=jobs))
            print(f'JOB {ds} {seed}: exit={r.returncode}',flush=True)
            if r.returncode:raise RuntimeError(f'Worker failed: {log}')
    assert len(jobs)==6
    save(out/'completion.json',dict(status='complete',jobs=jobs,records=90,wall_s=time.perf_counter()-start,freeze_sha256=sha(ROOT/'plan/freeze.json')))
    print('COMPLETE round27:6 jobs90 rows',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze() if a.freeze else run()

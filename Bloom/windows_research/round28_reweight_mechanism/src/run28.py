import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent
sys.path.insert(0,str(ROOT/'src'))
from worker28 import save,sha,SETTINGS
import subprocess
import time
import json


def freeze():
    assert not (ROOT/'plan/freeze.json').exists()
    paths=set((ROOT/'src').glob('*.py'))|{ROOT/'plan/design-freeze.md'}
    for directory in ('src','vendor/original_src','round2_backlog/src','round4_ra_plbf/src','round5_dp/src','round11_tcp/src','round12_nomodel/src','round22_kl_diagnostic_v2/src'):
        paths.update((WR/directory).glob('*.py'))
    # Covers legacy dataset initialization and source-only imports, never runtime artifacts.
    for mod in tuple(sys.modules.values()):
        name=getattr(mod,'__file__',None)
        if not name:continue
        p=Path(name).resolve()
        if p.is_relative_to(BLOOM) and not p.is_relative_to(BLOOM/'.condaenv') and p.suffix=='.py':paths.add(p)
    sources={str(p.relative_to(BLOOM)):sha(p) for p in sorted(paths)}
    from mechanism28 import E5
    inputs={str(p.relative_to(BLOOM)):sha(p) for ds in SETTINGS for name in ('data.npz','gama_scores.npz','model200.txt') for p in [E5.C.CACHE/ds/name]}
    save(ROOT/'plan/freeze.json',dict(created='2026-11-21',paper_commit='e256658',paper_path='vldb/sections/analysis.tex',sources=sources,inputs=inputs,expected_cases=168))
    print('FROZEN',len(sources),'sources',flush=True)


def run():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['inputs'].items():assert sha(BLOOM/p)==h,p
    jobs=[];start=time.perf_counter();out=ROOT/'results';out.mkdir(exist_ok=True)
    assert not (out/'completion.json').exists()
    for ds in SETTINGS:
        dest=out/f'{ds}.json';log=dest.with_suffix('.log');assert not dest.exists() and not log.exists()
        with log.open('x') as stream:r=subprocess.run([sys.executable,'-I',str(ROOT/'src/worker28.py'),ds,str(dest)],cwd=BLOOM,stdout=stream,stderr=subprocess.STDOUT)
        jobs.append(dict(dataset=ds,exit_code=r.returncode));save(out/'progress.json',dict(status='running' if r.returncode==0 else 'failed',jobs=jobs))
        print('JOB',ds,r.returncode,flush=True)
        if r.returncode:raise RuntimeError(f'Failed worker {log}')
    save(out/'completion.json',dict(status='complete',paired_cases=168,physical_builds=504,jobs=jobs,wall_s=time.perf_counter()-start,freeze_sha256=sha(ROOT/'plan/freeze.json')))
    print('COMPLETE round28:168cases504builds',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze() if a.freeze else run()

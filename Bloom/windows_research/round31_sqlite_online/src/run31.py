"""Frozen, sequential fresh workers; no automatic overwrite/resume."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker31 import ROOT,WR,BLOOM,SETTINGS,sha,save,E5
import subprocess
import json
import time


def freeze():
    p=ROOT/'plan/freeze.json';assert not p.exists()
    sources=set((ROOT/'src').glob('*.py'))|{ROOT/'plan/design-freeze.md'}
    for mod in tuple(sys.modules.values()):
        value=getattr(mod,'__file__',None)
        if not value:continue
        q=Path(value).resolve()
        if q.is_relative_to(BLOOM) and not q.is_relative_to(BLOOM/'.condaenv') and q.suffix=='.py':sources.add(q)
    inputs={}
    for ds,kib in SETTINGS.items():
        for name in ('data.npz','scores.npz','gama_scores.npz','model200.txt'):
            q=E5.C.CACHE/ds/name;assert q.exists();inputs[str(q.relative_to(BLOOM))]=sha(q)
        if ds.endswith('_flow'):
            q=E5.C.CACHE/ds/'trace.npy';inputs[str(q.relative_to(BLOOM))]=sha(q)
        q=WR/f'round6_bucket/results/e789/{ds}_{kib}.json';inputs[str(q.relative_to(BLOOM))]=sha(q)
    save(p,dict(date='2026-11-22',sources={str(q.relative_to(BLOOM)):sha(q) for q in sorted(sources)},inputs=inputs,settings=SETTINGS,expected_timing_records=312,repetitions=3,queries=200000))
    print('FROZEN',len(sources),'sources',len(inputs),'inputs',flush=True)


def run():
    manifest=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in manifest['inputs'].items():assert sha(BLOOM/p)==h,p
    out=ROOT/'results';out.mkdir(exist_ok=True);assert not (out/'completion.json').exists();start=time.perf_counter();jobs=[];records=0
    for ds in SETTINGS:
        dest=out/f'{ds}.json';log=dest.with_suffix('.log');assert not dest.exists() and not log.exists()
        with log.open('x') as f:r=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src/worker31.py'),ds,str(dest)],cwd=BLOOM,stdout=f,stderr=subprocess.STDOUT)
        jobs.append(dict(dataset=ds,exit_code=r.returncode));save(out/'progress.json',dict(status='running' if r.returncode==0 else 'failed',jobs=jobs))
        print('JOB',ds,'exit',r.returncode,flush=True)
        if r.returncode:raise RuntimeError(f'Worker failed; no auto-restart: {log}')
        data=json.loads(dest.read_text());assert data['status']=='complete';records+=len(data['timings'])
    assert records==312
    save(out/'completion.json',dict(status='complete',datasets=8,feasible_setting_methods=52,timing_records=records,jobs=jobs,wall_s=time.perf_counter()-start,freeze_sha256=sha(ROOT/'plan/freeze.json')))
    print('COMPLETE round31:8settings312timings',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze() if a.freeze else run()

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker34 import ROOT,WR,BLOOM,E5,SETTINGS,sha,save,DELAYS_US
from forecast34 import compute
import subprocess,json,time


def prerequisite():
    p=WR/'round33_gt_normalization_v2/results/verification.json'
    assert p.exists() and json.loads(p.read_text())['status']=='verified','Wait for GTv2 completion AND report verification before timing'


def freeze():
    prerequisite();p=ROOT/'plan/freeze.json';assert not p.exists()
    sources=set((ROOT/'src').glob('*.py'))|{ROOT/'plan/design-freeze.md'}
    for mod in tuple(sys.modules.values()):
        value=getattr(mod,'__file__',None)
        if not value:continue
        q=Path(value).resolve()
        if q.is_relative_to(BLOOM) and not q.is_relative_to(BLOOM/'.condaenv') and q.suffix=='.py':sources.add(q)
    forecast=compute();dest=ROOT/'results/pretrial_forecast.json'
    if dest.exists():assert json.loads(dest.read_text())==forecast
    else:save(dest,forecast)
    inputs={}
    for ds,kib in SETTINGS.items():
        for name in ('data.npz','scores.npz','gama_scores.npz','model200.txt'):
            q=E5.C.CACHE/ds/name;inputs[str(q.relative_to(BLOOM))]=sha(q)
        if ds.endswith('_flow'):
            q=E5.C.CACHE/ds/'trace.npy';inputs[str(q.relative_to(BLOOM))]=sha(q)
        for q in (WR/f'round31_sqlite_online/results/{ds}.json',WR/f'round6_bucket/results/e789/{ds}_{kib}.json'):inputs[str(q.relative_to(BLOOM))]=sha(q)
    for q in (dest,WR/'round31_sqlite_online/results/medians.csv'):inputs[str(q.relative_to(BLOOM))]=sha(q)
    save(p,dict(date='2026-11-22',sources={str(q.relative_to(BLOOM)):sha(q) for q in sorted(sources)},inputs=inputs,settings=SETTINGS,extra_us=DELAYS_US,queries=200000,reps=3,expected_timing_records=288))
    print('FROZEN',len(sources),'sources',len(inputs),'inputs;forecast recorded before measurement',flush=True)


def run():
    prerequisite();f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['inputs'].items():assert sha(BLOOM/p)==h,p
    out=ROOT/'results';assert not (out/'completion.json').exists();jobs=[];start=time.perf_counter();count=0
    for ds in SETTINGS:
        dest=out/f'{ds}.json';log=dest.with_suffix('.log');assert not dest.exists() and not log.exists()
        with log.open('x') as stream:r=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src/worker34.py'),ds,str(dest)],cwd=BLOOM,stdout=stream,stderr=subprocess.STDOUT)
        jobs.append(dict(dataset=ds,exit_code=r.returncode));save(out/'progress.json',dict(status='running' if r.returncode==0 else 'failed',jobs=jobs))
        print('JOB',ds,'exit',r.returncode,flush=True)
        if r.returncode:raise RuntimeError(f'Failed;no auto-retry:{log}')
        d=json.loads(dest.read_text());assert d['status']=='complete';count+=len(d['timings'])
    assert count==288
    save(out/'completion.json',dict(status='complete',settings=8,delays=6,methods=2,reps=3,timing_records=count,jobs=jobs,wall_s=time.perf_counter()-start,freeze_sha256=sha(ROOT/'plan/freeze.json')))
    print('COMPLETE backend-cost sensitivity:288timings',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze() if a.freeze else run()

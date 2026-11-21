import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker32 import ROOT,WR,BLOOM,E5,SETTINGS,sha,save
import subprocess,json,time


def freeze():
    p=ROOT/'plan/freeze.json';assert not p.exists()
    files=set((ROOT/'src').glob('*.py'))|{ROOT/'plan/design-freeze.md'}
    for mod in tuple(sys.modules.values()):
        name=getattr(mod,'__file__',None)
        if not name:continue
        q=Path(name).resolve()
        if q.is_relative_to(BLOOM) and not q.is_relative_to(BLOOM/'.condaenv') and q.suffix=='.py':files.add(q)
    inputs={}
    for ds,budgets in SETTINGS.items():
        for name in ('data.npz','scores.npz','gama_scores.npz','model200.txt'):
            q=E5.C.CACHE/ds/name;inputs[str(q.relative_to(BLOOM))]=sha(q)
        for kib in budgets:
            for folder in ('round5_dp/results','round6_bucket/results/main'):
                q=WR/folder/f'rows_{ds}_{kib}.csv';inputs[str(q.relative_to(BLOOM))]=sha(q)
    save(p,dict(date='2026-11-22',sources={str(q.relative_to(BLOOM)):sha(q) for q in sorted(files)},inputs=inputs,no_repeat_cases=140,repeated_controls=4,settings=SETTINGS))
    print('FROZEN',len(files),'sources',len(inputs),'inputs',flush=True)


def run():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['inputs'].items():assert sha(BLOOM/p)==h,p
    out=ROOT/'results';out.mkdir(exist_ok=True);assert not (out/'completion.json').exists();jobs=[];start=time.perf_counter();total=0
    for ds in SETTINGS:
        dest=out/f'{ds}.json';log=dest.with_suffix('.log');assert not dest.exists() and not log.exists()
        with log.open('x') as stream:r=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src/worker32.py'),ds,str(dest)],cwd=BLOOM,stdout=stream,stderr=subprocess.STDOUT)
        jobs.append(dict(dataset=ds,exit_code=r.returncode));save(out/'progress.json',dict(status='running' if r.returncode==0 else 'failed',jobs=jobs))
        print('JOB',ds,r.returncode,flush=True)
        if r.returncode:raise RuntimeError(f'Failed, no automatic retry:{log}')
        d=json.loads(dest.read_text());assert d['status']=='complete';total+=len(d['cases'])
    assert total==140;save(out/'completion.json',dict(status='complete',no_repeat_cases=140,repeated_controls=4,jobs=jobs,wall_s=time.perf_counter()-start,freeze_sha256=sha(ROOT/'plan/freeze.json')))
    print('COMPLETE NR32:140no-repeat cases and4repeated controls',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze() if a.freeze else run()

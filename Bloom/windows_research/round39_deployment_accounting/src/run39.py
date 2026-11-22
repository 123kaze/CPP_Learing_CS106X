"""Run only prespecified counting controls, one worker at a time."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from worker39 import check,sha,W
import json,subprocess,time


def main():
    start=time.perf_counter();frozen=check();f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['inputs'].items():assert sha(ROOT.parents[1]/p)==h,p
    assert not (ROOT/'results/progress.json').exists(),'Refuse run overwrite'
    done=[];W.save(ROOT/'results/progress.json',dict(status='running',jobs=done))
    for job in f['jobs']:
        ds,seed,mode=job['dataset'],job['seed'],job['cache']
        with (ROOT/f'results/{ds}_{seed}_{mode}.log').open('x') as log:
            p=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src/worker39.py'),ds,str(seed),mode],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT.parents[1])
        done.append(dict(**job,exit_code=p.returncode))
        W.save(ROOT/'results/progress.json',dict(status='running' if p.returncode==0 else 'failed',jobs=done))
        print('ACCOUNT_WORKER',ds,seed,mode,'exit',p.returncode,flush=True)
        if p.returncode:raise RuntimeError('Worker failed; no automatic retry')
    from report39 import main as report
    v=report();W.save(ROOT/'results/completion.json',dict(status='complete',settings=v['settings'],comparisons=v['comparisons'],scenario_projections=v['scenario_projections'],workers=len(done),wall_s=time.perf_counter()-start,freeze_sha256=frozen))
    W.save(ROOT/'results/progress.json',dict(status='complete',jobs=done));check()
    print('COMPLETE_ROUND39',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as e:
        W.save(ROOT/'results/failure.json',dict(status='failed',error=repr(e)))
        raise

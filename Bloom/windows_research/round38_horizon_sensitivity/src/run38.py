"""Sequential one-cache-per-process execution; no retries or overwrite."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from horizon38 import ROOT,W,check_freeze,sha
import json,subprocess,time


def main():
    start=time.perf_counter();frozen=check_freeze()
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['inputs'].items():assert sha(ROOT.parents[1]/p)==h,p
    assert not (ROOT/'results/progress.json').exists(),'Refuse automatic restart'
    progress=[];W.save(ROOT/'results/progress.json',dict(status='running',jobs=progress))
    for job in freeze['jobs']:
        ds,seed,mode=job['dataset'],job['seed'],job['cache']
        log=ROOT/f'results/{ds}_{seed}_{mode}.log'
        with log.open('x') as f:
            process=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src/worker38.py'),ds,str(seed),mode],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT.parents[1])
        progress.append(dict(**job,exit_code=process.returncode))
        W.save(ROOT/'results/progress.json',dict(status='running' if process.returncode==0 else 'failed',jobs=progress))
        print('WORKER38',ds,seed,mode,'exit',process.returncode,flush=True)
        if process.returncode:raise RuntimeError('Worker failed; logs retained; no automatic restart')
    from report38 import main as report
    verification=report()
    W.save(ROOT/'results/completion.json',dict(status='complete',rows=verification['rows'],workers=len(progress),
        wall_s=time.perf_counter()-start,freeze_sha256=frozen))
    W.save(ROOT/'results/progress.json',dict(status='complete',jobs=progress))
    check_freeze();print('COMPLETE_ROUND38',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:
        W.save(ROOT/'results/failure.json',dict(status='failed',error=repr(error)))
        raise

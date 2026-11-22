"""Sequential frozen workers; failures are retained and never automatically restarted."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from control37 import ROOT,SEEDS,W,check_freeze
import subprocess
import time


def main():
    check_freeze();start=time.perf_counter()
    assert not (ROOT/'results/progress.json').exists(), 'Refuse run overwrite'
    progress=[]
    W.save(ROOT/'results/progress.json',dict(status='running',jobs=progress))
    for seed in SEEDS:
        log=ROOT/f'results/seed{seed}.log'
        with log.open('x') as f:
            p=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src/worker37.py'),str(seed)],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT.parents[1])
        progress.append(dict(seed=seed,exit_code=p.returncode))
        W.save(ROOT/'results/progress.json',dict(status='running' if p.returncode==0 else 'failed',jobs=progress))
        print('WORKER',seed,'exit',p.returncode,flush=True)
        if p.returncode:raise RuntimeError(f'Worker {seed} failed; no automatic retry')
    from report37 import main as report
    verified=report()
    W.save(ROOT/'results/completion.json',dict(status='complete',main_rows=verified['main_rows'],control_rows=verified['control_rows'],
                                              jobs=progress,wall_s=time.perf_counter()-start,freeze_sha256=check_freeze()))
    W.save(ROOT/'results/progress.json',dict(status='complete',jobs=progress))
    print('COMPLETE_ROUND37',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as e:
        W.save(ROOT/'results/failure.json',dict(status='failed',error=repr(e)))
        raise

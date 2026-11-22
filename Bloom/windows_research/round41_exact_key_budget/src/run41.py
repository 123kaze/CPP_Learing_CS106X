import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data41 import ROOT,BLOOM,W,check
import subprocess,time,shutil


def main():
    check();assert shutil.disk_usage(BLOOM).free>=2*1024**3;start=time.perf_counter()
    completion=ROOT/'results/completion.json';assert not completion.exists()
    for name,args in [('final_unit_checks',['test41.py']),('raw_extract',['data41.py']),*[(f'seed{s}',['worker41.py',str(s)]) for s in (3601,3602,3603)],('report',['report41.py'])]:
        log=ROOT/f'results/{name}.log';assert not log.exists()
        t=time.perf_counter()
        with log.open('x') as f:
            try:r=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdout=f,stderr=subprocess.STDOUT,timeout=1200,check=True)
            except BaseException as e:
                W.save(ROOT/'results/failure.json',dict(stage=name,error=repr(e),status='failed',wall_s=time.perf_counter()-start));raise
        print('STAGE_COMPLETE',name,round(time.perf_counter()-t,3),flush=True)
        assert time.perf_counter()-start<3600
    check();W.save(completion,dict(status='complete',wall_s=time.perf_counter()-start));print('ROUND41_COMPLETE',flush=True)

if __name__=='__main__':main()

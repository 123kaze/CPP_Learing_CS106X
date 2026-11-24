import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data44 import *
import subprocess,shutil


def launch(name,args,timeout):
    log=ROOT/f'results/{name}.log';start=time.perf_counter()
    with log.open('x') as f:subprocess.run([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
    print('STAGE_COMPLETE',name,round(time.perf_counter()-start,3),flush=True)


def main():
    check();assert json.loads((ROOT/'results/downloads.json').read_text())['status']=='complete';assert shutil.disk_usage(ROOT).free>=2*1024**3;start=time.perf_counter()
    assert not (ROOT/'results/completion.json').exists()
    try:
        launch('final_unit_checks',['test44.py'],120)
        for cluster in CLUSTERS:launch(f'{cluster}_qualification',['qualify44.py',cluster],600)
        # Qualification of every fixed candidate completes before ANY methodFP is measured.
        eligible=[c for c in CLUSTERS if json.loads((ROOT/f'results/{c}_qualification.json').read_text())['eligible_for_method_comparison']]
        save(ROOT/'results/qualification_complete.json',dict(status='complete',eligible=eligible,all_fixed_candidates_audited=True,method_FP_not_yet_measured=True))
        for cluster in eligible:
            for seed in SEEDS:launch(f'{cluster}_{seed}',['worker44.py',cluster,str(seed)],1200)
        launch('report',['report44.py'],120);check()
        save(ROOT/'results/completion.json',dict(status='complete',wall_s=time.perf_counter()-start,eligible=eligible));print('ROUND44_COMPLETE',flush=True)
    except BaseException as e:save(ROOT/'results/failure.json',dict(status='failed',error=repr(e),wall_s=time.perf_counter()-start));raise

if __name__=='__main__':main()

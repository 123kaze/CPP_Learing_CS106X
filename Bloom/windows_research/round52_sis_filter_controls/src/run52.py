import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker52 import ROOT,BLOOM,check,save,RECIPES,SEEDS
import subprocess,time,json,shutil


def launch(name,args,timeout=1200):
    start=time.perf_counter();peak=0;proc=None
    with (ROOT/f'results/{name}.log').open('x') as log:
        try:
            proc=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            while proc.poll() is None:
                if time.perf_counter()-start>timeout:raise TimeoutError(f'{name}deadline')
                ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=5)
                if ps.returncode==0 and ps.stdout.strip():
                    rss=int(ps.stdout.strip())*1024;peak=max(peak,rss)
                    if rss>=4*1024**3:raise MemoryError(f'{name}RSSlimit; no automatic restart')
                if shutil.disk_usage(ROOT).free<8*1024**3:raise RuntimeError('Diskreserve')
                time.sleep(.5)
            assert proc.returncode==0,f'{name}exit{proc.returncode}'
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
    save(ROOT/f'results/{name}_process.json',dict(status='complete',wall_s=time.perf_counter()-start,observed_peak_rss_bytes=peak));print('STAGE_COMPLETE',name,round(time.perf_counter()-start,3),flush=True)


def main():
    check();start=time.perf_counter();assert not (ROOT/'results/completion.json').exists()
    try:
        launch('final_unit_checks',['test52.py'],120);launch('pilot',['worker52.py','balanced_clip','5001','--pilot'])
        pilot=json.loads((ROOT/'results/pilot.json').read_text());assert pilot['status']=='complete';estimate=18*pilot['wall_s'];passed=estimate<=7200 and pilot['peak_rss_bytes']<4*1024**3
        save(ROOT/'results/pilot_gate.json',dict(passed=passed,predicted_formal_s=estimate,limit_s=7200,pilot_wall_s=pilot['wall_s'],peak_rss_bytes=pilot['peak_rss_bytes'],no_outcome_or_AUC_gate=True))
        assert passed,'Resource/time gate failed; no matrix changes'
        for recipe in RECIPES:
            for seed in SEEDS:launch(f'{recipe}_{seed}',['worker52.py',recipe,str(seed)])
        launch('report',['report52.py'],120);check();save(ROOT/'results/completion.json',dict(status='complete',wall_s=time.perf_counter()-start));print('ROUND52_COMPLETE',flush=True)
    except BaseException as e:save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-start,no_automatic_retry=True));raise

if __name__=='__main__':main()

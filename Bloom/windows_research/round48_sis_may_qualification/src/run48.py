import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data48 import ROOT,BLOOM,SEEDS,check,save
import subprocess,time,json,shutil


def launch(name,args,timeout):
    proc=None;started=time.perf_counter();peak=0
    with (ROOT/f'results/{name}.log').open('x') as log:
        try:
            proc=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            while proc.poll() is None:
                if time.perf_counter()-started>timeout:raise TimeoutError(f'{name}deadline')
                ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=5)
                if ps.returncode==0 and ps.stdout.strip():
                    rss=int(ps.stdout.strip())*1024;peak=max(peak,rss)
                    if rss>4*1024**3:raise MemoryError(f'{name}RSSlimit; no automatic restart')
                time.sleep(.5)
            assert proc.returncode==0,f'{name}exit{proc.returncode}'
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
    save(ROOT/f'results/{name}_process.json',dict(status='complete',seconds=time.perf_counter()-started,observed_peak_rss_bytes=peak));print('STAGE_COMPLETE',name,round(time.perf_counter()-started,3),flush=True)


def main():
    check();assert json.loads((ROOT.parent/'round48_sis_extract_v2/results/extraction.json').read_text())['status']=='verified';assert shutil.disk_usage(ROOT).free>=8*1024**3;assert not (ROOT/'results/completion.json').exists();start=time.perf_counter()
    try:
        launch('final_unit_checks',['test48.py'],30);launch('parse',['data48.py'],180)
        for seed in SEEDS:launch(f'diagnostic_{seed}',['qualify48.py',str(seed)],120)
        launch('report',['report48.py'],60);check();q=json.loads((ROOT/'results/qualification.json').read_text())
        save(ROOT/'results/completion.json',dict(status='complete',eligible=q['eligible_for_method_comparison'],wall_s=time.perf_counter()-start));print('ROUND48_QUALIFICATION_COMPLETE',q['eligible_for_method_comparison'],flush=True)
    except BaseException as e:save(ROOT/'results/qualification_failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-start,no_automatic_retry=True));raise

if __name__=='__main__':main()

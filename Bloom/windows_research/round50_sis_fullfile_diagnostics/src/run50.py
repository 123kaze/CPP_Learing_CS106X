import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare50 import ROOT,BLOOM,check,save,SEEDS
import subprocess,time,json,shutil


def launch(name,args,timeout):
    proc=None;t=time.perf_counter();peak=0
    with (ROOT/f'results/{name}.log').open('x') as f:
        try:
            proc=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
            while proc.poll() is None:
                if time.perf_counter()-t>timeout:raise TimeoutError(f'{name}deadline')
                ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=5)
                if ps.returncode==0 and ps.stdout.strip():
                    rss=int(ps.stdout.strip())*1024;peak=max(peak,rss)
                    if rss>4*1024**3:raise MemoryError(f'{name}RSSlimit; no automatic restart')
                if shutil.disk_usage(ROOT).free<8*1024**3:raise RuntimeError('Diskreserve')
                time.sleep(.5)
            assert proc.returncode==0,f'{name}exit{proc.returncode}'
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
    save(ROOT/f'results/{name}_process.json',dict(status='complete',wall_s=time.perf_counter()-t,peak_rss_bytes=peak));print('STAGE_COMPLETE',name,round(time.perf_counter()-t,3),flush=True)


def main():
    check();assert not (ROOT/'results/completion.json').exists();t=time.perf_counter()
    try:
        launch('final_unit_checks',['test50.py'],60);launch('preparation',['prepare50.py'],1800)
        for s in SEEDS:launch(f'seed{s}',['diagnose50.py',str(s)],600)
        launch('report',['report50.py'],60);check();q=json.loads((ROOT/'results/qualification.json').read_text())
        save(ROOT/'results/completion.json',dict(status='complete',wall_s=time.perf_counter()-t,eligible=q['eligible_for_method_comparison'],exploratory_not_holdout=True));print('ROUND50_COMPLETE',q['eligible_for_method_comparison'],flush=True)
    except BaseException as e:save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-t,no_automatic_retry=True));raise

if __name__=='__main__':main()

"""Serial bounded experiment runner. No failed stage is automatically retried."""
import sys,subprocess,shutil,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shared54 import ROOT,BLOOM,WR,save,check,TCP,CMATRIX,DMATRIX,sha


def launch(name,args,timeout=1800):
    start=time.perf_counter();proc=None;peak=0;status='failed';error=None
    try:
        assert shutil.disk_usage(ROOT).free>=4*1024**3,'Disk reserve below4GiB'
        with (ROOT/f'results/{name}.log').open('x') as log:
            proc=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            while proc.poll() is None:
                if time.perf_counter()-start>timeout:raise TimeoutError(name+' deadline; no automatic retry')
                ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=5)
                if ps.returncode==0 and ps.stdout.strip():
                    rss=int(ps.stdout.strip())*1024;peak=max(peak,rss)
                    if rss>=4*1024**3:raise MemoryError(name+' RSS limit; user decision required')
                if shutil.disk_usage(ROOT).free<4*1024**3:raise RuntimeError('Disk reserve')
                if sum(p.stat().st_size for p in (ROOT/'results').rglob('*') if p.is_file())>512*1024**2:raise RuntimeError('Output cap')
                time.sleep(1)
            assert proc.returncode==0,f'{name} exit {proc.returncode}'
        status='complete'
    except BaseException as e:error=f'{type(e).__name__}: {e}';raise
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        save(ROOT/f'results/{name}_process.json',dict(status=status,error=error,wall_s=time.perf_counter()-start,peak_observed_RSS=peak,exit_code=proc.returncode if proc else None))
    print('STAGE_COMPLETE',name,round(time.perf_counter()-start,3),flush=True)


def main():
    start=time.perf_counter();(ROOT/'results').mkdir(parents=True,exist_ok=True)
    assert not (ROOT/'results/failure.json').exists() and not (ROOT/'results/completion.json').exists()
    try:
        launch('tests',['test54.py'],120);launch('freeze',['freeze54.py'],120);check()
        launch('audit',['audit54.py'],120)
        for ds in TCP:launch('zero_'+ds,['methods54.py','zero',ds])
        for seed in (3601,3602,3603):launch('zero_clark_'+str(seed),['methods54.py','zero','clark','--seed',str(seed)])
        launch('zero_url',['methods54.py','zero','url'])
        for ds in CMATRIX:launch('coupled_'+ds,['methods54.py','coupled',ds])
        for ds in DMATRIX:launch('online_'+ds,['online54.py',ds],3600)
        launch('report',['report54.py'],120);check()
        save(ROOT/'results/completion.json',dict(status='complete',wall_s=time.perf_counter()-start))
        print('ROUND54_COMPLETE',round(time.perf_counter()-start,3),flush=True)
    except BaseException as e:save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-start,no_automatic_retry=True));raise

if __name__=='__main__':main()

"""One experiment worker at a time; strict fixed pilot gate, no automatic retries."""
import sys,subprocess,shutil,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common56 import *
LIMIT=8*1024**3


def stop(p):
    if p.poll() is None:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait()


def child(name,args,campaign_start,timeout=3600):
    out=ROOT/'results';start=time.perf_counter();epoch=time.time();peak=0;p=None
    try:
        with (out/f'{name}.log').open('x') as log:
            p=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*map(str,args[1:])],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            print('START',name,'pid',p.pid,flush=True)
            while p.poll() is None:
                if time.time()-epoch>timeout:raise TimeoutError(name+' worker deadline')
                if time.time()-campaign_start>28800:raise TimeoutError('8hour campaign deadline')
                if shutil.disk_usage(ROOT).free<4*1024**3:raise RuntimeError('disk below4GiB reserve')
                q=subprocess.run(['/bin/ps','-o','rss=','-p',str(p.pid)],capture_output=True,text=True,timeout=5)
                if q.returncode==0 and q.stdout.strip():
                    peak=max(peak,int(q.stdout.strip())*1024)
                    if peak>=LIMIT:raise MemoryError('8GiB RSS limit; no automatic retry')
                time.sleep(1)
            if p.returncode:raise RuntimeError(name+f' exit{p.returncode}')
        elapsed=time.perf_counter()-start
        save(out/f'{name}_process.json',dict(status='complete',exit_code=0,wall_s=elapsed,elapsed_epoch_s=time.time()-epoch,peak_observed_rss=peak,serial=True))
        print('COMPLETE',name,round(elapsed,3),flush=True)
        return elapsed
    except BaseException as e:
        if p is not None:stop(p)
        save(out/f'{name}_process.json',dict(status='failed',error_type=type(e).__name__,error=str(e),exit_code=None if p is None else p.returncode,wall_s=time.perf_counter()-start,peak_observed_rss=peak))
        raise


def main():
    start=time.time();clock=time.perf_counter();out=ROOT/'results';out.mkdir(parents=True,exist_ok=True)
    assert not (ROOT/'plan/freeze.json').exists()
    finished=[]
    try:
        save(out/'environment.json',dict(platform=platform.platform(),machine=platform.machine(),python=sys.version,cpu_count=os.cpu_count(),load_average=os.getloadavg(),disk_free_bytes=shutil.disk_usage(ROOT).free,epoch_start=start,parallel_experiment_workers=0))
        child('tests',['test56.py'],start,120)
        child('freeze',['freeze56.py'],start,120);freeze_check(inputs=True)
        pilots=[]
        for ds,k in (('url',128),('caida',256)):
            for m in METHODS:pilots.append(child(f'pilot_{ds}_{k}_{m}',['worker56.py',ds,k,m,0,'--pilot'],start))
        estimate=72*max(pilots)+120
        save(out/'pilot_gate.json',dict(status='passed' if estimate<=28800 else 'failed',pilot_worker_wall_s=pilots,estimated_formal_s=estimate,limit_s=28800,rule='72*slowest_pilot_worker+120; no pilot reused as formal'))
        assert estimate<=28800,'fixed8h cost gate not passed'
        for ds,k in SETTINGS:
            for rep in range(REPS):
                for m in order(rep):
                    name=f'{ds}_{k}_rep{rep}_{m}'
                    child(name,['worker56.py',ds,k,m,rep],start)
                    finished.append(name)
                    used=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
                    assert used<128*1024**2,'output cap'
                    # Versioned progress receipts are immutable.
                    save(out/f'progress_{len(finished):03d}.json',dict(status='running',completed_workers=len(finished),total_workers=72,last=name,elapsed_s=time.perf_counter()-clock))
        child('report',['report56.py'],start,120);freeze_check(inputs=True)
        save(out/'completion.json',dict(status='complete',formal_workers=len(finished),pilot_workers=6,wall_s=time.perf_counter()-clock,elapsed_epoch_s=time.time()-start,max_workers=1,scope='Current full-pool exact selection only; fresh training/query/scalability not included'))
        print('ROUND56_COMPLETE',flush=True)
    except BaseException as e:
        save(out/'failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),completed_workers=finished,wall_s=time.perf_counter()-clock,no_automatic_retry=True))
        raise


if __name__=='__main__':main()

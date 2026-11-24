import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
import subprocess,shutil


def launch(name,args,timeout=1800):
    start=time.perf_counter();peak=0;proc=None;status='failed';error=None
    try:
        with (ROOT/f'results/{name}.log').open('x') as log:
            proc=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            while proc.poll() is None:
                if time.perf_counter()-start>timeout:raise TimeoutError(f'{name}: deadline; no automatic retry')
                ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=5)
                if ps.returncode==0 and ps.stdout.strip():
                    rss=int(ps.stdout.strip())*1024;peak=max(peak,rss)
                    if rss>=4*1024**3:raise MemoryError(f'{name}: RSS limit; no automatic restart')
                if shutil.disk_usage(ROOT).free<8*1024**3:raise RuntimeError('8GiB disk reserve')
                time.sleep(.5)
            assert proc.returncode==0,f'{name}: exit {proc.returncode}'
        status='complete'
    except BaseException as e:error=f'{type(e).__name__}: {e}';raise
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        save(ROOT/f'results/{name}_process.json',dict(status=status,error=error,wall_s=time.perf_counter()-start,observed_peak_rss_bytes=peak,exit_code=proc.returncode if proc else None))
    print('STAGE_COMPLETE',name,round(time.perf_counter()-start,3),flush=True)


def archive():
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or any(x in p.parts for x in ('cache','__pycache__')) or p.name=='archive_manifest.json':continue
        if p.suffix not in ('.py','.md','.json','.csv','.log') and p.name!='.gitignore':continue
        files.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)))
    save(ROOT/'archive_manifest.json',dict(files=files))


def main():
    start=time.perf_counter();check_sources()
    assert not (ROOT/'results/completion.json').exists() and not (ROOT/'results/failure.json').exists()
    try:
        launch('unit_checks',['test53.py'],120)
        for ds in ('url','caida_flow'):launch(f'raw_{ds}',['prepare53.py',ds])
        launch('pilot_url_64',['worker53.py','url','64','--pilot'])
        launch('pilot_caida_flow_16',['worker53.py','caida_flow','16','--pilot'])
        url=json.loads((ROOT/'results/pilot_url_64.json').read_text());flow=json.loads((ROOT/'results/pilot_caida_flow_16.json').read_text())
        forecast=url['wall_s']/3*42+flow['wall_s']*20
        passed=forecast<=7200
        save(ROOT/'results/pilot_gate.json',dict(passed=passed,estimated_matrix_s=forecast,limit_s=7200,no_FP_or_AUC_gate=True,note='rough schema-stratified pilot projection; actual per-worker and global caps still enforced'))
        assert passed,'Pilot resource forecast exceeded fixed matrix limit'
        formal_start=time.perf_counter()
        for ds in DATASETS:
            if ds not in ('url','caida_flow'):launch(f'raw_{ds}',['prepare53.py',ds],min(1800,max(1,7200-(time.perf_counter()-formal_start))))
            for kib in BUDGETS[ds]:
                remaining=7200-(time.perf_counter()-formal_start)
                assert remaining>0,'Formal matrix deadline; no automatic retry'
                launch(f'{ds}_{kib}',['worker53.py',ds,str(kib)],min(1800,remaining))
        launch('report',['report53.py'],120)
        check_sources();save(ROOT/'results/completion.json',dict(status='complete',cases=62,rows=434,wall_s=time.perf_counter()-start,formal_matrix_s=time.perf_counter()-formal_start))
        archive();print('ROUND53_COMPLETE',round(time.perf_counter()-start,3),flush=True)
    except BaseException as e:
        save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-start,no_automatic_retry=True));archive();raise


if __name__=='__main__':main()

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
                    if rss>=6*1024**3:raise MemoryError(f'{name}: RSS limit; no automatic restart')
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
        provenance=json.loads((ROOT/'results/reuse_provenance.json').read_text())
        assert provenance['status']=='verified' and provenance['reused_cases']==38
        for item in provenance['files']:
            assert sha(ROOT/item['path'])==sha(BLOOM/item['source'])==item['sha256']
        for item in provenance['prepared_inputs']:assert sha(ROOT/item['path'])==item['sha256']
        assert json.loads((ROOT/'results/pilot_gate.json').read_text())['passed']
        formal_start=time.perf_counter()
        for ds in ('caida','shalla'):
            if ds=='shalla':launch(f'raw_{ds}',['prepare53.py',ds],min(1800,max(1,7200-(time.perf_counter()-formal_start))))
            for kib in BUDGETS[ds]:
                remaining=7200-(time.perf_counter()-formal_start)
                assert remaining>0,'Formal matrix deadline; no automatic retry'
                launch(f'{ds}_{kib}',['worker53.py',ds,str(kib)],min(1800,remaining))
        launch('report',['report53.py'],120)
        check_sources();save(ROOT/'results/completion.json',dict(status='complete',cases=62,rows=434,reused_v2_cases=38,reused_v2_rows=266,new_v3_cases=24,new_v3_rows=168,RSS_limit_bytes=6*1024**3,wall_s=time.perf_counter()-start,extension_matrix_s=time.perf_counter()-formal_start))
        archive();print('ROUND53_COMPLETE',round(time.perf_counter()-start,3),flush=True)
    except BaseException as e:
        save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-start,no_automatic_retry=True));archive();raise


if __name__=='__main__':main()

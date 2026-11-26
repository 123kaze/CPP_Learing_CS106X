import sys,subprocess,shutil,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common55 import ROOT,BLOOM,save,freeze_check,case_manifest


def launch(name,args,timeout=7200):
    start=time.perf_counter();proc=None;peak=0;status='failed';error=None
    try:
        assert shutil.disk_usage(ROOT).free>=4*1024**3,'Disk below4GiB reserve'
        with (ROOT/f'results/{name}.log').open('x') as log:
            proc=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            while proc.poll() is None:
                if time.perf_counter()-start>timeout:raise TimeoutError(name+' deadline; no automatic retry')
                p=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=5)
                if p.returncode==0 and p.stdout.strip():
                    rss=int(p.stdout.strip())*1024;peak=max(peak,rss)
                    if rss>=4*1024**3:raise MemoryError(name+' RSS limit; do not restart without user decision')
                if shutil.disk_usage(ROOT).free<4*1024**3:raise RuntimeError('Disk reserve')
                if sum(p.stat().st_size for p in (ROOT/'results').rglob('*') if p.is_file())>1024**3:raise RuntimeError('Output cap1GiB')
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
    assert not (ROOT/'plan/freeze.json').exists() and not (ROOT/'results/failure.json').exists()
    try:
        launch('tests',['test55.py'],120);launch('freeze',['freeze55.py'],120);freeze_check()
        for ds,k in (('url',64),('caida',128),('mawi2021_flow',24)):launch(f'pilot_{ds}_{k}',['worker55.py',ds,str(k),'--pilot'])
        pilot=[]
        for ds,k in (('url',64),('caida',128),('mawi2021_flow',24)):
            root=ROOT/f'results/pilot_{ds}_{k}';st=json.loads((root/'status.json').read_text());assert st['status']=='complete'
            items=[json.loads((root/p).read_text()) for p in st['case_files']];assert all(c['regression53'] for c in items)
            pilot.append(dict(dataset=ds,budget_kib=k,wall_s=st['wall_s'],cases=len(items),mean_case_s=sum(c['wall_s'] for c in items)/len(items),peak_RSS=st['peak_rss_bytes']))
        static=max(x['mean_case_s'] for x in pilot if not x['dataset'].endswith('_flow'));flow=pilot[-1]['mean_case_s']
        estimate=1130*static+20*flow+34*max(x['wall_s']-x['mean_case_s']*x['cases'] for x in pilot)
        passed=estimate<=28800;save(ROOT/'results/pilot_gate.json',dict(passed=passed,estimated_full_main_s=estimate,limit_s=28800,pilots=pilot,no_FP_gate=True,scope='Conservative case-time extrapolation from fixed pilot; not a measured full-campaign time. If over limit, stop for explicit resource decision.'))
        assert passed,'Pilot forecast exceeds8h predeclared gate; no matrix reduction'
        formal=time.perf_counter()
        for setting in case_manifest()['settings']:
            remaining=28800-(time.perf_counter()-formal);assert remaining>0,'8h formal deadline'
            ds,k=setting['dataset'],setting['budget_kib'];launch(f'{ds}_{k}',['worker55.py',ds,str(k)],min(7200,remaining))
        launch('report',['report55.py'],120);freeze_check();save(ROOT/'results/completion.json',dict(status='complete',main_cases=1146,MAWI24_cases=4,formal_wall_s=time.perf_counter()-formal,wall_s=time.perf_counter()-start))
        print('ROUND55_COMPLETE',flush=True)
    except BaseException as e:save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-start,no_automatic_retry=True));raise

if __name__=='__main__':main()

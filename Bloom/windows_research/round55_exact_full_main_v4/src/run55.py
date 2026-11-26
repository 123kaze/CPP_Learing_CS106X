"""User-authorized two-worker scheduler, original numerical/replay implementations unchanged."""
import sys,subprocess,shutil,time,json,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common55 import ROOT,BLOOM,WR,save,sha,freeze_check,case_manifest
MAX_WORKERS=2;RSS_LIMIT=8*1024**3;TOTAL_RSS=16*1024**3;BATCH=8*3600;TOTAL=5*24*3600


def serial(name,args,timeout=120):
    start=time.perf_counter()
    with (ROOT/f'results/{name}.log').open('x') as f:
        p=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    save(ROOT/f'results/{name}_process.json',dict(status='complete' if p.returncode==0 else 'failed',wall_s=time.perf_counter()-start,exit_code=p.returncode))
    assert p.returncode==0,f'{name} exit {p.returncode}'


def stop(job):
    p=job['proc']
    if p.poll() is None:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait()


def finish(job,status,error=None):
    p=job['proc'];job['log'].close()
    save(ROOT/f"results/{job['name']}_process.json",dict(status=status,error=error,wall_s=time.perf_counter()-job['start'],peak_observed_RSS=job['peak'],exit_code=p.returncode,max_simultaneous_workers=MAX_WORKERS,timing_scope='concurrent FP campaign; not uncontended selection/construction timing'))


def main():
    start=time.perf_counter();out=ROOT/'results';out.mkdir(parents=True,exist_ok=True);active={};completed=[];remaining=[]
    assert not (ROOT/'plan/freeze.json').exists() and not (out/'failure.json').exists()
    try:
        # Verify replay/select code has not changed, apart from explicit host-memory assertion.
        old=WR/'round55_exact_full_main_v3/src'
        assert (ROOT/'src/common55.py').read_bytes()==(old/'common55.py').read_bytes()
        new=(ROOT/'src/worker55.py').read_text().replace("assert meta['peak_rss_bytes']<8*1024**3","assert meta['peak_rss_bytes']<4*1024**3")
        assert new==(old/'worker55.py').read_text()
        serial('tests',['test55.py']);serial('freeze',['freeze55.py']);freeze_check()
        reuse=json.loads((ROOT/'plan/reuse.json').read_text());assert reuse['completed_pilot_cases_reused']==7 and reuse['formal_cases_reused']==0
        for r in reuse['files']:assert sha(ROOT/r['target'])==sha(BLOOM/r['source'])==r['sha256']
        for ds,k in (('url',64),('caida',128),('mawi2021_flow',24)):
            p=out/f'pilot_{ds}_{k}';s=json.loads((p/'status.json').read_text());assert s['status']=='complete'
            for name in s['case_files']:assert json.loads((p/name).read_text())['regression53']
        save(out/'resource_authorization.json',dict(original_8h_gate_preserved=str((WR/'round55_exact_full_main_v3/results/pilot_gate.json').relative_to(BLOOM)),user_chose_original_implementation_no_optimization=True,user_authorized_parallel_after_single_thread_choice=True,complete_pilot_cases=7,formal_cases_reused=0,max_workers=MAX_WORKERS,worker_RSS_limit=RSS_LIMIT,aggregate_RSS_limit=TOTAL_RSS,batch_deadline_s=BATCH,total_deadline_s=TOTAL,native_threads_per_worker=1,note='Parallel independent budget workers; each keeps original numerical thread settings. Not a change to deployment Filter Budget or claims of zero-FN.'))
        remaining=list(case_manifest()['settings']);formal=time.perf_counter();last_state=0
        save(out/'start.json',dict(status='running',pid=os.getpid(),start_epoch=time.time(),settings=len(remaining),main_cases=1146,additional_cases=4))
        while remaining or active:
            now=time.perf_counter()
            if now-formal>TOTAL:raise TimeoutError('User-authorized5day total deadline')
            if shutil.disk_usage(ROOT).free<4*1024**3:raise RuntimeError('Disk below4GiB reserve')
            while remaining and len(active)<MAX_WORKERS:
                setting=remaining.pop(0);ds,k=setting['dataset'],setting['budget_kib'];name=f'{ds}_{k}'
                assert not (out/name).exists();log=(out/f'{name}.log').open('x')
                p=subprocess.Popen([sys.executable,'-I','-u',str(ROOT/'src/worker55.py'),ds,str(k)],cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                active[name]=dict(name=name,proc=p,log=log,start=time.perf_counter(),peak=0,case_count=len(setting['cases']))
                print('WORKER_STARTED',name,'pid',p.pid,'cases',len(setting['cases']),flush=True)
            total_rss=0
            for name,j in list(active.items()):
                p=j['proc'];code=p.poll()
                if code is not None:
                    if code!=0:
                        finish(j,'failed',f'Worker exit{code}');del active[name];raise RuntimeError(f'{name} exit {code}; original logs retained')
                    s=json.loads((out/name/'status.json').read_text());assert s['status']=='complete' and s['cases_completed']==j['case_count']
                    finish(j,'complete');completed.append(dict(setting=name,cases=j['case_count'],wall_s=time.perf_counter()-j['start']));del active[name]
                    print('SETTING_COMPLETE',name,j['case_count'],'cases',flush=True);continue
                if now-j['start']>BATCH:raise TimeoutError(name+'8hour batch limit')
                q=subprocess.run(['/bin/ps','-o','rss=','-p',str(p.pid)],capture_output=True,text=True,timeout=5)
                if q.returncode==0 and q.stdout.strip():
                    rss=int(q.stdout.strip())*1024;total_rss+=rss;j['peak']=max(j['peak'],rss)
                    if rss>=RSS_LIMIT:raise MemoryError(name+'8GiB RSS safety limit; no automatic restart')
            if total_rss>=TOTAL_RSS:raise MemoryError('16GiB aggregate worker RSS safety limit')
            if now-last_state>=30:
                used=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
                if used>1024**3:raise RuntimeError('1GiB output cap')
                save(out/'progress.json',dict(status='running',completed_settings=completed,remaining_settings=len(remaining),active=[dict(setting=j['name'],pid=j['proc'].pid,elapsed_s=now-j['start'],peak_observed_RSS=j['peak']) for j in active.values()],current_worker_RSS=total_rss,wall_s=now-formal))
                last_state=now
            time.sleep(1)
        serial('report',['report55.py']);freeze_check()
        save(out/'completion.json',dict(status='complete',main_cases=1146,MAWI24_cases=4,completed_settings=completed,formal_wall_s=time.perf_counter()-formal,wall_s=time.perf_counter()-start,max_workers=MAX_WORKERS,scope='FP correctness and graph source data; parallel timings not publishable as uncontended timing benchmarks'))
        print('ROUND55_V4_COMPLETE',flush=True)
    except BaseException as e:
        for j in active.values():stop(j);finish(j,'aborted_after_campaign_stop',f'{type(e).__name__}: {e}')
        save(out/'failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-start,completed_settings=completed,remaining_settings=len(remaining),no_automatic_retry=True));raise

if __name__=='__main__':main()

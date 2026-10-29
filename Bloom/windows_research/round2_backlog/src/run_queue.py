"""Durable sequential worker queues; no background job is called completed early."""
from pathlib import Path
import sys,argparse,subprocess,time,json,datetime
ROOT=Path(__file__).resolve().parents[1]
QUEUES={
 'stacked_a':[['run_stacked.py','--dataset','cod'],['run_stacked.py','--dataset','shalla'],['run_stacked.py','--dataset','caida_flow'],['run_stacked.py','--dataset','mawi2021_flow']],
 'stacked_b':[['run_stacked.py','--dataset','caida']],
 'aqf':[['run_aqf.py','--dataset',ds,'--budget',str(kib)] for ds,kib in [('cod',4096),('caida',2048),('shalla',4096),('caida_flow',256),('mawi2021_flow',128)]],
}
def main(name):
    jobs=[];dest=ROOT/'results'/f'queue-{name}.json'
    for number,args in enumerate(QUEUES[name]):
        log=ROOT/'results'/f'{name}-{number}.log'
        row=dict(args=args,log=str(log.relative_to(ROOT)),status='running',start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        jobs.append(row);dest.write_text(json.dumps(jobs,indent=2),encoding='utf-8');start=time.perf_counter()
        with log.open('w',encoding='utf-8') as out:
            result=subprocess.run([sys.executable,'-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
        row.update(status='passed' if result.returncode==0 else 'failed',returncode=result.returncode,seconds=time.perf_counter()-start)
        dest.write_text(json.dumps(jobs,indent=2),encoding='utf-8')
        if result.returncode:raise RuntimeError(log)
    (ROOT/'results'/f'queue-{name}.done').write_text('all child processes exited successfully',encoding='utf-8')
    print('COMPLETE',name,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name',choices=QUEUES);a=p.parse_args();main(a.name)

"""Sequential CPU runs; status/logs persist and timing runs remain separate."""
from pathlib import Path
import subprocess,sys,json,time,datetime
ROOT=Path(__file__).resolve().parents[1]
status=ROOT/'results'/'suite-status.json'
history=[]
def save():status.write_text(json.dumps(history,indent=2),encoding='utf-8')
def job(args,log):
    start=time.time()
    row=dict(command=[sys.executable]+args,log=str(log),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='running')
    history.append(row);save()
    with (ROOT/log).open('w',encoding='utf-8') as f:
        r=subprocess.run([sys.executable]+args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    row.update(status='passed' if r.returncode==0 else 'failed',returncode=r.returncode,elapsed_seconds=time.time()-start)
    save()
    if r.returncode:raise RuntimeError(f'Failed: {args}, see {log}')
# Existing Caida CLOCK process owns the CPU first.
deadline=time.time()+1800
target=ROOT/'results'/'rerun_v2_caida_clock'/'run_meta.json'
while not target.exists():
    if time.time()>deadline:raise TimeoutError('Caida CLOCK did not finish; inspect log')
    time.sleep(2)
for ds,backend in [('cod','global_lru'),('caida','global_lru'),('caida_flow','clock'),('caida_flow','global_lru')]:
    job(['src/run_experiments.py','--dataset',ds,'--backend',backend],f'results/rerun_v2_{ds}_{backend}.log')
job(['src/freeze_holdout.py','verify'],'results/holdout-precheck.log')
for backend in ('clock','global_lru'):
    job(['src/run_experiments.py','--dataset','mawi2021_flow','--backend',backend],f'results/rerun_v2_mawi2021_flow_{backend}.log')
job(['src/freeze_holdout.py','verify'],'results/holdout-postcheck.log')
print('ALL RERUNS COMPLETE',flush=True)

"""Finish the explicitly requested suite after the sequential accuracy runs."""
from pathlib import Path
import json,sys,subprocess,time,datetime
ROOT=Path(__file__).resolve().parents[1]
status=ROOT/'results'/'finish-status.json'
jobs=[]
def save():status.write_text(json.dumps(jobs,indent=2),encoding='utf-8')
def run(args,log):
    dest=ROOT/log;dest.parent.mkdir(exist_ok=True,parents=True)
    row=dict(command=[sys.executable]+args,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='running',log=str(log))
    jobs.append(row);save();started=time.perf_counter()
    with dest.open('w',encoding='utf-8') as out:
        result=subprocess.run([sys.executable]+args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
    row.update(status='passed' if result.returncode==0 else 'failed',elapsed_seconds=time.perf_counter()-started,returncode=result.returncode);save()
    if result.returncode:raise RuntimeError(f'Failed {args}; see {log}')
deadline=time.time()+3600
while True:
    p=ROOT/'results'/'suite-status.json'
    if p.exists():
        rows=json.loads(p.read_text(encoding='utf-8'))
        if any(r['status']=='failed' for r in rows):raise RuntimeError('Accuracy suite failed; inspect logs')
        if rows and rows[-1]['log']=='results/holdout-postcheck.log' and rows[-1]['status']=='passed':break
    if time.time()>deadline:raise TimeoutError('Accuracy suite has not completed')
    time.sleep(3)
for ds,budgets in [('cod','256,1024'),('caida','128,256')]:
    run(['src/end_to_end.py','--dataset',ds,'--budgets',budgets,'--output-dir','results/end_to_end_fixed'],f'results/end_to_end_fixed/run_{ds}.log')
run(['src/verify_suite.py'],'evidence/suite-verification.log')
run(['src/audit_existing.py','verify'],'evidence/protected-verification.log')
run(['src/summarize_results.py'],'results/summarize.log')
print('ALL REQUESTED EXPERIMENTS AND VERIFICATION COMPLETE',flush=True)

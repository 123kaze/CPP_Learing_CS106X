"""Resume only failed/pending holdout jobs; retain first-attempt evidence."""
from pathlib import Path
import json,sys,time,subprocess,datetime
ROOT=Path(__file__).resolve().parents[1]
dest=ROOT/'results'/'suite-status.json'
rows=json.loads(dest.read_text(encoding='utf-8'))
rows=[r for r in rows if r['status']=='passed']
def save():dest.write_text(json.dumps(rows,indent=2),encoding='utf-8')
save()
def run(args,log):
    row=dict(command=[sys.executable]+args,log=log,status='running',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),repair_evidence='evidence/holdout-repair.md')
    rows.append(row);save();t=time.perf_counter()
    with (ROOT/log).open('w',encoding='utf-8') as out:
        result=subprocess.run([sys.executable]+args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
    row.update(status='passed' if result.returncode==0 else 'failed',returncode=result.returncode,elapsed_seconds=time.perf_counter()-t);save()
    if result.returncode:raise RuntimeError(log)
run(['src/freeze_holdout.py','verify'],'results/holdout-amended-precheck.log')
for backend in ('clock','global_lru'):
    run(['src/run_experiments.py','--dataset','mawi2021_flow','--backend',backend],f'results/rerun_v2_mawi2021_flow_{backend}.log')
run(['src/freeze_holdout.py','verify'],'results/holdout-postcheck.log')
print('HOLDOUT COMPLETE WITH DISCLOSED BASELINE-GUARD REPAIR',flush=True)

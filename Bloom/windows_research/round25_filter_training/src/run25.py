import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import json
import sys
import time
import subprocess
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for kind in ('sources','inputs'):
        for p,h in freeze[kind].items():assert digest(BLOOM/p)==h,p
    dest=ROOT/'results/main';dest.mkdir(exist_ok=True)
    for ds in ('url','caida_tcp_flow'):
        for seed in (1,2,3):
            p=dest/f'{ds}_seed{seed}.json'
            if p.exists():
                r=json.loads(p.read_text());assert r['status']=='complete' and r['exit_code']==0
                continue
            log=p.with_suffix('.log');assert not log.exists(),'Partial log, no automatic retry'
            t=time.perf_counter();print('START',ds,seed,flush=True)
            with log.open('x') as f:proc=subprocess.run([sys.executable,'-u',str(ROOT/'src/worker25.py'),'--dataset',ds,'--seed',str(seed),'--output',str(p)],stdout=f,stderr=subprocess.STDOUT)
            r=json.loads(p.read_text()) if p.exists() else dict(status='error',error=f'exit{proc.returncode}')
            r.update(exit_code=proc.returncode,process_wall_s=time.perf_counter()-t);p.write_text(json.dumps(r,indent=2)+'\n')
            if proc.returncode or r['status']!='complete':print(log.read_text()[-4000:],flush=True);raise SystemExit(1)
            assert len(r['records'])==8
            print('COMPLETE',ds,seed,f'{r["process_wall_s"]:.1f}s',flush=True)
    for p,h in freeze['sources'].items():assert digest(BLOOM/p)==h
    (ROOT/'results/completion.json').write_text(json.dumps(dict(status='complete',jobs=6,filter_records=48,initialization_seeds=[1,2,3],freeze_sha256=digest(ROOT/'plan/freeze.json')),indent=2)+'\n')
    print('ROUND25 COMPLETE:matched-capacity loss comparison,48 records,no cache',flush=True)


if __name__=='__main__':main()

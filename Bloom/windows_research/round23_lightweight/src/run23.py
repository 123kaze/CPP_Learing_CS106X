"""Six serial independent training processes; repeated native timing inside each."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import subprocess
import sys
import json
import time
import hashlib
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for rel,h in freeze[section].items():assert digest(BLOOM/rel)==h,rel
    dest=ROOT/'results/main';dest.mkdir(parents=True,exist_ok=True)
    total=0
    for ds in ('url','caida_tcp_flow'):
        for rep in range(3):
            p=dest/f'{ds}_rep{rep}.json'
            if p.exists():
                r=json.loads(p.read_text());assert r['status']=='complete' and r['exit_code']==0
            else:
                log=p.with_suffix('.log');assert not log.exists(),'Partial log; no automatic retry'
                start=time.perf_counter();print(f'START {ds} rep{rep}',flush=True)
                with log.open('x') as f:
                    proc=subprocess.run([sys.executable,'-u',str(ROOT/'src/worker23.py'),'--dataset',ds,'--rep',str(rep),'--output',str(p)],stdout=f,stderr=subprocess.STDOUT)
                r=json.loads(p.read_text()) if p.exists() else dict(status='failed',error=f'worker exit {proc.returncode}')
                r.update(exit_code=proc.returncode,process_wall_s=time.perf_counter()-start)
                p.write_text(json.dumps(r,indent=2)+'\n')
                if proc.returncode or r['status']!='complete':
                    print(log.read_text()[-5000:],flush=True);raise SystemExit(1)
            assert len(r['models'])==6 and len(r['filters'])==14
            assert r['rep']==rep and r['dataset']==ds
            total+=len(r['filters'])
            print(f'COMPLETE {ds} rep{rep}: {total}/84 filter records',flush=True)
    for rel,h in freeze['sources'].items():assert digest(BLOOM/rel)==h
    (ROOT/'results/completion.json').write_text(json.dumps(dict(status='complete',jobs=6,model_trainings=36,filter_records=84,
                protocol_sha256=digest(ROOT/'plan/design-freeze.md'),freeze_sha256=digest(ROOT/'plan/freeze.json')),indent=2)+'\n')
    print('ROUND23 COMPLETE:36 scorer trainings,84 physically budgeted filter records,all member/native checks',flush=True)


if __name__=='__main__':main()

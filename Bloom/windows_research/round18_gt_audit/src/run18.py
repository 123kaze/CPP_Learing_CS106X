"""Run actual-data audits serially; no experimental selector is executed."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[v]='1'
from pathlib import Path
import subprocess
import sys
import json
ROOT=Path(__file__).resolve().parents[1]
DATASETS=('caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow','mawi2024_flow','cod','url','caida','shalla')


def main():
    for ds in DATASETS:
        out=ROOT/f'results/{ds}.json'
        if out.exists():
            assert json.loads(out.read_text())['status']=='complete',out
            continue
        log=out.with_suffix('.log');assert not log.exists(),'Partial audit log exists; do not silently retry'
        print(f'START read-only audit {ds}',flush=True)
        with log.open('x') as f:p=subprocess.run([sys.executable,'-u',str(ROOT/'src/audit18.py'),'--dataset',ds],stdout=f,stderr=subprocess.STDOUT)
        if p.returncode:
            print(log.read_text()[-3000:],flush=True);raise SystemExit(p.returncode)
        r=json.loads(out.read_text());assert r['status']=='complete'
        print(f'COMPLETE {ds}: {len(r["cases"])} cases, gaps in {sum(bool(s["gap_c"]) for s in r["streams"])} stream groups',flush=True)
    results=[json.loads((ROOT/f'results/{ds}.json').read_text()) for ds in DATASETS]
    assert sum(len(r['cases']) for r in results)==1150
    assert sum(len(r['streams']) for r in results)==325
    (ROOT/'results/completion.json').write_text(json.dumps(dict(status='complete',main_cases=1146,holdout_cases=4,stream_groups=325,datasets=9),indent=2)+'\n')
    print('AUDIT COMPLETE: actual 1146 main cases + 4 MAWI24 cases; no selectors rerun',flush=True)


if __name__=='__main__':main()

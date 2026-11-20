import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
import hashlib,json,sys,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for rel,h in f[group].items():assert digest(BLOOM/rel)==h,rel
    dest=ROOT/'results/main';dest.mkdir(exist_ok=True)
    for ds in ('url','caida_tcp_flow','caida'):
        out=dest/f'{ds}.json'
        if out.exists():
            r=json.loads(out.read_text());assert r['status']=='complete' and r['exit_code']==0;continue
        log=out.with_suffix('.log');assert not log.exists(),'Partial log, no automatic retry'
        start=time.perf_counter();print('START',ds,flush=True)
        with log.open('x') as fh:p=subprocess.run([sys.executable,'-u',str(ROOT/'src/worker26.py'),'--dataset',ds,'--output',str(out)],stdout=fh,stderr=subprocess.STDOUT)
        r=json.loads(out.read_text()) if out.exists() else dict(status='error',error=f'worker exit{p.returncode}')
        r.update(exit_code=p.returncode,process_wall_s=time.perf_counter()-start);out.write_text(json.dumps(r,indent=2)+'\n')
        if p.returncode or r['status']!='complete':print(log.read_text()[-4000:],flush=True);raise SystemExit(1)
        assert len(r['results'])==36
        print('COMPLETE',ds,len(r['results']),'records',flush=True)
    for rel,h in f['sources'].items():assert digest(BLOOM/rel)==h,rel
    (ROOT/'results/completion.json').write_text(json.dumps(dict(status='complete',jobs=3,trained_comparison_models=9,reference_models=3,configurations=108,
        freeze_sha256=digest(ROOT/'plan/freeze.json')),indent=2)+'\n')
    print('ROUND26 COMPLETE:LightGBM unchanged,three negative-weight arms,108 configurations',flush=True)


if __name__=='__main__':main()

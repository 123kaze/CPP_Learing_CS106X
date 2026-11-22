"""Run both preselected workload audits once, sequentially, without outcome-based filtering."""
import os
for _v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fetch36 import save,sha,FILES
from data36 import parse
from diagnose36 import diagnose,qualify,SEEDS
import json
import platform
import resource
import time
import numpy as np
import lightgbm as lgb
import scipy


def check_freeze():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    return sha(ROOT/'plan/freeze.json')


def main():
    start=time.perf_counter();frozen=check_freeze()
    assert not (ROOT/'results/input-manifest.json').exists(), 'Refuse automatic audit restart/overwrite'
    downloads=json.loads((ROOT/'results/downloads.json').read_text())
    assert downloads['status']=='complete' and len(downloads['files'])==3
    inputs={}
    for name,filename,size in FILES:
        r=next(r for r in downloads['files'] if r['name']==name)
        path=ROOT/'inputs'/name/'assembled'/filename
        assert str(path.relative_to(ROOT))==r['path'] and r['crc_verified']
        assert path.stat().st_size==size==r['compressed_bytes'] and sha(path)==r['sha256']
        inputs[name]=dict(path=str(path.relative_to(ROOT)),sha256=r['sha256'])
    save(ROOT/'results/input-manifest.json',dict(freeze_sha256=frozen,inputs=inputs,
         download_receipt_sha256=sha(ROOT/'results/downloads.json'),platform=platform.platform(),python=platform.python_version(),
         numpy=np.__version__,lightgbm=lgb.__version__,scipy=scipy.__version__))
    settings=(('clarknet',('clarknet_aug28','clarknet_sep4')),('sask',('sask',)))
    for name,sources in settings:
        t=time.perf_counter();output=ROOT/f'results/{name}.json';assert not output.exists()
        prepared=ROOT/f'cache/{name}.npz'
        meta=parse([ROOT/inputs[s]['path'] for s in sources],prepared,name)
        diagnostics=[]
        for seed in SEEDS:
            d=diagnose(prepared,seed);diagnostics.append(d)
            print('DIAGNOSTIC',name,seed,'AUC',d['development_auc'],'repeat_gap',d['region_repeat_gap'],flush=True)
        q=qualify(meta,diagnostics)
        save(output,dict(status='complete',dataset=name,data=meta,diagnostics=diagnostics,qualification=q,
                         wall_s=time.perf_counter()-t,freeze_sha256=frozen,
                         peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)))
        print('QUALIFICATION',name,'PASS' if q['eligible_for_full_comparison'] else 'FAIL',','.join(q['failed_checks']),flush=True)
        check_freeze()
    from report36 import report
    verified=report()
    save(ROOT/'results/completion.json',dict(status='complete',workloads=2,diagnostic_rows=6,eligible=verified['eligible'],
         wall_s=time.perf_counter()-start,freeze_sha256=frozen,filter_effects_measured=False))
    print('COMPLETE_ROUND36',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as e:
        save(ROOT/'results/failure.json',dict(status='failed',error=repr(e)))
        raise

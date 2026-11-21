import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker33 import ROOT,WR,BLOOM,E5,DATASETS,CACHES,ARMS,cases,reference_rows,sha,save
import subprocess,json,time


def preflight():
    rows=reference_rows()
    for c in cases():
        for mode in CACHES:assert (c['dataset'],c['budget_kib'],c['workload'],c['seed'],mode) in rows,(c,mode)
    print('PREFLIGHT:30case keys,60same-format archived controls',flush=True)


def freeze():
    preflight();p=ROOT/'plan/freeze.json';assert not p.exists()
    files=set((ROOT/'src').glob('*.py'))|{ROOT/'plan/design-freeze.md'}
    for mod in tuple(sys.modules.values()):
        name=getattr(mod,'__file__',None)
        if not name:continue
        q=Path(name).resolve()
        if q.is_relative_to(BLOOM) and not q.is_relative_to(BLOOM/'.condaenv') and q.suffix=='.py':files.add(q)
    inputs={}
    for ds in DATASETS:
        for name in ('data.npz','scores.npz','gama_scores.npz','model200.txt'):
            q=E5.C.CACHE/ds/name;inputs[str(q.relative_to(BLOOM))]=sha(q)
        if ds.endswith('_flow'):
            q=E5.C.CACHE/ds/'trace.npy';inputs[str(q.relative_to(BLOOM))]=sha(q)
    for rel in ('round18_gt_audit/results/affected_cases.json','round19_gt_fix/results/updated_main_comparisons.csv'):
        q=WR/rel;inputs[str(q.relative_to(BLOOM))]=sha(q)
    save(p,dict(date='2026-11-22',sources={str(q.relative_to(BLOOM)):sha(q) for q in sorted(files)},inputs=inputs,cases=cases(),arms=ARMS,cache_formats=list(CACHES),expected_rows=180))
    print('FROZEN',len(files),'sources',len(inputs),'inputs',flush=True)


def run():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['inputs'].items():assert sha(BLOOM/p)==h,p
    out=ROOT/'results';out.mkdir(exist_ok=True);assert not (out/'completion.json').exists();start=time.perf_counter();jobs=[];records=0
    for ds in DATASETS:
        for mode in CACHES:
            dest=out/f'{ds}_{mode}.json';log=dest.with_suffix('.log');assert not dest.exists() and not log.exists()
            with log.open('x') as stream:r=subprocess.run([sys.executable,'-I','-u',str(ROOT/'src/worker33.py'),ds,mode,str(dest)],cwd=BLOOM,stdout=stream,stderr=subprocess.STDOUT)
            jobs.append(dict(dataset=ds,cache=mode,exit_code=r.returncode));save(out/'progress.json',dict(status='running' if r.returncode==0 else 'failed',jobs=jobs))
            print('JOB',ds,mode,'exit',r.returncode,flush=True)
            if r.returncode:raise RuntimeError(f'Failed;no automatic retry:{log}')
            d=json.loads(dest.read_text());assert d['status']=='complete';records+=sum(len(c['arms']) for c in d['cases'])
    assert records==180
    save(out/'completion.json',dict(status='complete',case_keys=30,cache_specific_cases=60,arm_records=records,jobs=jobs,wall_s=time.perf_counter()-start,freeze_sha256=sha(ROOT/'plan/freeze.json')))
    print('COMPLETE GT normalization:180arm records',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--preflight',action='store_true');a=p.parse_args()
    preflight() if a.preflight else freeze() if a.freeze else run()

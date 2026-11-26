"""Freeze timing code and exact inputs before pilots; no changes to round55."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common56 import *
from datetime import datetime,timezone
from importlib.metadata import version


def main():
    assert read(C.ROOT/'results/completion.json')['status']=='complete'
    assert read(BLOOM/'docs/round55_evidence_20261126/final_audit/verification.json')['status']=='complete_evidence_audit_passed'
    old=read(C.ROOT/'plan/freeze.json');sources=dict(old['sources'])
    for name,digest in sources.items():assert sha(BLOOM/name)==digest,name
    for p in list((ROOT/'src').glob('*.py'))+[ROOT/'plan/design-freeze.md',ROOT/'.gitignore']:
        sources[str(p.relative_to(BLOOM))]=sha(p)
    inputs={}
    for ds,k in SETTINGS:
        p,_=reference(ds,k)
        for q in C.input_paths(ds)+[p]:inputs[str(q.relative_to(BLOOM))]=sha(q)
    for p in (C.ROOT/'plan/freeze.json',C.ROOT/'plan/cases.json',C.ROOT/'results/completion.json',BLOOM/'docs/round55_evidence_20261126/final_audit/verification.json'):
        inputs[str(p.relative_to(BLOOM))]=sha(p)
    save(ROOT/'plan/freeze.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),sources=sources,inputs=inputs,
         settings=SETTINGS,methods=METHODS,reps=REPS,formal_workers=72,pilot_workers=6,formal_results_reused=0,
         python=sys.version,versions={n:version(n) for n in ('numpy','numba','lightgbm','scipy')},
         RSS_limit_bytes=8*1024**3,disk_reserve_bytes=4*1024**3,output_limit_bytes=128*1024**2,
         worker_deadline_s=3600,campaign_deadline_s=28800,max_workers=1,native_threads=1))
    print('FROZEN_SELECTION56',len(sources),'sources',len(inputs),'inputs',flush=True)


if __name__=='__main__':main()

"""60 fresh, serial constructions with alternating loop/leaf order and exact checks."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import lightgbm as lgb
from check_scoring import check

ROOT=Path(__file__).resolve().parents[1]
WR=ROOT.parent


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    p=path.with_suffix('.json.tmp');p.write_text(json.dumps(data,indent=2)+'\n');p.replace(path)


def main():
    baseline=json.loads((ROOT/'results/baseline_completion.json').read_text())
    assert baseline['status']=='complete','Do not overlap timing with baseline jobs'
    freeze=json.loads((ROOT/'plan/scoring-freeze.json').read_text())
    for rel,want in freeze['sha256'].items():assert digest(WR/rel)==want,rel
    dest=ROOT/'results/scoring';dest.mkdir(parents=True,exist_ok=True)
    data_root=WR/'round8_paper_data'
    files=[]
    for ds in ('paper_url','paper_cod'):
        files.append(data_root/'data'/ds/'data.npz')
        files += [data_root/'inputs'/ds/f'{name}_{part}.npy' for name in ('once','zipf') for part in ('learn','tail')]
    manifest=dict(datasets=['paper_url','paper_cod'],budgets=[64,128,192,256,320],reps=3,chunk_rows=32768,
                  python=sys.version,numpy=np.__version__,lightgbm=lgb.__version__,platform=platform.platform(),
                  inputs={str(p.relative_to(WR)):digest(p) for p in files},sources=freeze['sha256'],
                  note='Serial fresh paired runs; hashes outside construction stages; no new official-Gama timings.')
    mp=dest/'manifest.json'
    if mp.exists():assert json.loads(mp.read_text())==manifest,'Do not mix changed inputs/code/environment'
    else:save(mp,manifest)
    checks=[]
    for ds in manifest['datasets']:
        for kib in manifest['budgets']:
            for rep in range(3):
                pair={}
                order=('loop','leaf') if rep%2==0 else ('leaf','loop')
                for mode in order:
                    p=dest/f'{ds}_{kib}_{mode}_rep{rep}.json'
                    if p.exists():
                        row=json.loads(p.read_text())
                        assert row['status']=='ok' and row.get('rep')==rep and 'process_wall_s' in row,f'Failed/incomplete existing run: {p}'
                    else:
                        print(f'START scoring {ds} {kib} rep{rep} {mode}',flush=True)
                        begin=time.perf_counter()
                        with p.with_suffix('.log').open('w') as log:
                            proc=subprocess.run([sys.executable,'-u',str(ROOT/'src/scoring_worker.py'),ds,str(kib),str(p),
                                                 '--scoring',mode,'--chunk-rows','32768'],stdout=log,stderr=subprocess.STDOUT)
                        elapsed=time.perf_counter()-begin
                        row=json.loads(p.read_text()) if p.exists() else dict(status='error',error=f'worker exit {proc.returncode}')
                        row.update(rep=rep,process_wall_s=elapsed,exit_code=proc.returncode)
                        save(p,row)
                        if proc.returncode or row['status']!='ok':
                            print(f'FAILED {p.name}: {row.get("error","unknown error")}',flush=True)
                            raise SystemExit(1)
                        print(f'COMPLETE scoring {ds} {kib} rep{rep} {mode}: process {elapsed:.1f}s',flush=True)
                    pair[mode]=row
                result=check(pair['loop'],pair['leaf'])
                archived=json.loads((data_root/'results'/f'{ds}_{kib}_RA6_rep{rep}.json').read_text())
                assert archived['status']=='ok'
                for workload in ('once','zipf'):
                    old,new=archived['workloads'][workload],pair['loop']['workloads'][workload]
                    for key in ('trees','frac','cache_bytes','used_bytes','fp','fn','queries'):
                        assert old[key]==new[key],('round8 mismatch',ds,kib,rep,workload,key)
                    if workload=='once':assert old['pool']['fp']==new['pool']['fp']
                result['matches_round8_configs_and_counts']=True
                result['rep']=rep
                checks.append(result)
                save(dest/'pair_checks.json',checks)
                print(f'CHECKED {ds} {kib} rep{rep}: all score bits, configurations, BF payloads and native FPs identical',flush=True)
    assert len(checks)==30
    save(dest/'completion.json',dict(status='complete',fresh_builds=60,verified_pairs=30,verified_workload_pairs=60,
                                    prefixes_per_pair=14,manifest_sha256=digest(mp)))
    print('SCORING COMPLETE: 60 builds, 30 exact pairs',flush=True)


if __name__=='__main__':main()

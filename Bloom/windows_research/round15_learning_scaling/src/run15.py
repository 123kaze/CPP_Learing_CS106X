"""Single-thread, serial runs. No failed/partial result is silently retried."""
import os
for v in ('OMP_NUM_THREADS', 'NUMBA_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[v] = '1'
import json
import platform
import subprocess
import sys
import time
from common15 import *


def check_rows(pair):
    for r in pair.values():
        assert r['status']=='ok' and r['exit_code']==0 and r['selection_s']>0
        assert r['choice']['member_false_negatives']==0 and r['choice']['verified_full_build']
        assert r['built']==(5 if r['method']=='ra6' else r['candidates'])
    for key in ('L','rep','dataset','budget_kib','horizon','candidate_grid_sha256','stream_sha256','distinct_keys'):
        assert pair['ra6'][key]==pair['replay'][key],key
    assert pair['ra6']['choice']['keys_sha256']==pair['replay']['choice']['keys_sha256']


def worker(folder, L, rep, method, pilot=False):
    output = folder/f'L{L}_rep{rep}_{method}.json'
    if output.exists():
        r=json.loads(output.read_text())
        assert r.get('status')=='ok' and r.get('exit_code')==0 and r.get('L')==L and r.get('rep')==rep and 'process_wall_s' in r, f'Failed/partial result: {output}'
        return r
    log=output.with_suffix('.log')
    assert not log.exists(), f'Partial log, no automatic retry: {log}'
    cmd=[sys.executable,'-u',str(ROOT/'src/worker15.py'),'--method',method,'--length',str(L),'--rep',str(rep),'--output',str(output)]
    if pilot:cmd.append('--pilot')
    print(f'START {folder.name} L={L} rep={rep} {method}',flush=True)
    start=time.perf_counter()
    with log.open('x') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    elapsed=time.perf_counter()-start
    r=json.loads(output.read_text()) if output.exists() else dict(status='error',error=f'worker exit {p.returncode}')
    r.update(process_wall_s=elapsed,exit_code=p.returncode)
    save(output,r)
    if p.returncode or r['status']!='ok':
        print(f'FAILED {output.name}: exit={p.returncode}; see {log}',flush=True)
        print(log.read_text()[-4000:],flush=True)
        raise SystemExit(1)
    print(f'COMPLETE {folder.name} L={L} rep={rep} {method}: selection={r["selection_s"]:.3f}s process={elapsed:.1f}s',flush=True)
    return r


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,want in freeze['sources'].items():assert digest(BLOOM/rel)==want,rel
    for rel,want in freeze['inputs'].items():assert digest(BLOOM/rel)==want,rel
    subprocess.run([sys.executable,'-u',str(ROOT/'src/prepare15.py')],check=True)
    stream=json.loads((ROOT/'inputs/manifest.json').read_text())
    cfg=dict(lengths=LENGTHS,reps=REPS,dataset=DATASET,budget_kib=KIB,stream=stream,
             sources=freeze['sources'],input_cache_hashes=freeze['inputs'],python=sys.version,platform=platform.platform())
    mp=ROOT/'results/manifest.json'
    if mp.exists():assert json.loads(mp.read_text())==json.loads(json.dumps(cfg)), 'Inputs/source/environment changed'
    else:save(mp,cfg)
    pilot=ROOT/'results/pilot';pilot.mkdir(exist_ok=True)
    pair={m:worker(pilot,PILOT_L,0,m,True) for m in ('ra6','replay')};check_rows(pair)
    assert pair['ra6']['choice']['canonical_ra6_check']
    assert pair['replay']['choice']['no_cutoff_grid_check'] and pair['replay']['choice']['full_pool_replay_check']
    save(pilot/'completion.json',dict(status='complete',workers=2))
    print('PILOT PASSED; starting 42 formal workers',flush=True)
    dest=ROOT/'results/main';dest.mkdir(exist_ok=True)
    checks=[];grid=None
    for i,L in enumerate(LENGTHS):
        for rep in range(REPS):
            order=('ra6','replay') if (i+rep)%2==0 else ('replay','ra6')
            pair={m:worker(dest,L,rep,m) for m in order};check_rows(pair)
            if grid is None:grid=pair['ra6']['candidate_grid_sha256']
            assert pair['ra6']['candidate_grid_sha256']==grid
            checks.append(dict(L=L,rep=rep,matched_inputs_and_candidates=True))
            save(dest/'pair_checks.json',checks)
    assert len(list(dest.glob('L*_rep*_*.json')))==42
    save(dest/'completion.json',dict(status='complete',workers=42,pairs=21,lengths=7,
                                    manifest_sha256=digest(mp)))
    print('ROUND15 COMPLETE: 1M to 100M queries, 42 successful workers, 21 matched pairs',flush=True)


if __name__=='__main__':main()

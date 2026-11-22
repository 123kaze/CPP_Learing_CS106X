"""Unit-tested source freeze -> bounded pilot -> resource gate -> full local TCP run."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker35 import ROOT,WR,BLOOM,SETTINGS,sha,save
from online31 import E5
import backend35,reference35
import subprocess,json,time


def freeze():
    p=ROOT/'plan/freeze.json';assert not p.exists()
    sources=set((ROOT/'src').glob('*.py'))|{ROOT/'plan/design-freeze.md'}
    for mod in tuple(sys.modules.values()):
        name=getattr(mod,'__file__',None)
        if not name:continue
        q=Path(name).resolve()
        if q.is_relative_to(BLOOM) and not q.is_relative_to(BLOOM/'.condaenv') and q.suffix=='.py':sources.add(q)
    inputs={}
    for ds in SETTINGS:
        for name in ('data.npz','scores.npz','gama_scores.npz','model200.txt'):
            q=E5.C.CACHE/ds/name;inputs[str(q.relative_to(BLOOM))]=sha(q)
        if ds.endswith('_flow'):
            q=E5.C.CACHE/ds/'trace.npy';inputs[str(q.relative_to(BLOOM))]=sha(q)
        for round_name in ('round31_sqlite_online','round34_backend_cost'):
            q=WR/round_name/f'results/{ds}.json';inputs[str(q.relative_to(BLOOM))]=sha(q)
    save(p,dict(date='2026-11-22',sources={str(q.relative_to(BLOOM)):sha(q) for q in sorted(sources)},inputs=inputs,settings=SETTINGS,
                pilot_settings=['url','caida_flow'],pilot_queries=2000,formal_queries=200000,formal_reps=3,methods=['NoFilter','BF+Cache','RA6'],
                expected_formal_rows=72,max_estimated_seconds=3600,pilot_max_combined_rss_bytes=16*1024**3))
    print('FROZEN',len(sources),'sources',len(inputs),'inputs',flush=True)


def worker(ds,folder,pilot):
    folder.mkdir(parents=True,exist_ok=True);dest=folder/f'{ds}.json';log=dest.with_suffix('.log');assert not dest.exists() and not log.exists()
    args=[sys.executable,'-I','-u',str(ROOT/'src/worker35.py'),ds,str(dest)]+(['--pilot'] if pilot else [])
    with log.open('x') as f:r=subprocess.run(args,cwd=BLOOM,stdout=f,stderr=subprocess.STDOUT)
    print('WORKER',ds,'pilot' if pilot else 'formal','exit',r.returncode,flush=True)
    if r.returncode:raise RuntimeError(f'Worker failed; no automatic restart:{log}')
    d=json.loads(dest.read_text());assert d['status']=='complete' and d['pilot']==pilot
    return d


def run(pilot=False):
    manifest=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in manifest['inputs'].items():assert sha(BLOOM/p)==h,p
    start=time.perf_counter();jobs=[];count=0
    if pilot:
        gate=ROOT/'results/pilot_gate.json';assert not gate.exists();pilots=[]
        for ds in manifest['pilot_settings']:pilots.append(worker(ds,ROOT/'results/pilot',True))
        worst_ns=max(r['ns_per_query'] for p in pilots for r in p['timings'])
        known_setup=0
        for ds in SETTINGS:
            prior=json.loads((WR/f'round31_sqlite_online/results/{ds}.json').read_text());prepare=json.loads((WR/f'round34_backend_cost/results/{ds}.json').read_text())
            known_setup+=next(x['create_s'] for x in prior['databases'] if x['backend']=='file')+prepare['preparation']['prepare_and_reconstruct_s']
        estimate=worst_ns/1e9*200000*3*3*8*1.5+known_setup*2+60
        peak=max(p['client_peak_rss_bytes']+max(r['server_statistics']['peak_rss_bytes'] for r in p['timings']) for p in pilots)
        ok=estimate<=manifest['max_estimated_seconds'] and peak<=manifest['pilot_max_combined_rss_bytes']
        save(gate,dict(status='passed' if ok else 'blocked',correctness_verified=True,pilot_rows=sum(len(p['timings']) for p in pilots),
                       worst_observed_ns_per_query=worst_ns,conservative_estimated_formal_seconds=estimate,max_estimated_seconds=manifest['max_estimated_seconds'],
                       max_observed_combined_pilot_rss_bytes=peak,resource_threshold_bytes=manifest['pilot_max_combined_rss_bytes'],
                       selection_based_on_relative_method_win=False,wall_s=time.perf_counter()-start))
        print('PILOT GATE',ok,'estimated_seconds',estimate,'peak_bytes',peak,flush=True)
        if not ok:raise RuntimeError('Pilot resource/time gate blocked formal run; no automatic downsizing')
        return
    assert json.loads((ROOT/'results/pilot_gate.json').read_text())['status']=='passed'
    dest=ROOT/'results/completion.json';assert not dest.exists()
    for ds in SETTINGS:
        try:d=worker(ds,ROOT/'results/main',False)
        except Exception:
            save(ROOT/'results/progress.json',dict(status='failed',jobs=jobs,failed_dataset=ds));raise
        count+=len(d['timings']);jobs.append(dict(dataset=ds,status='complete',rows=len(d['timings'])))
        save(ROOT/'results/progress.json',dict(status='running',jobs=jobs))
    assert count==72
    save(dest,dict(status='complete',settings=8,methods=3,reps=3,formal_timing_rows=count,pilot_rows=6,jobs=jobs,wall_s=time.perf_counter()-start,freeze_sha256=sha(ROOT/'plan/freeze.json')))
    print('COMPLETE local TCP:72formal timings',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--pilot',action='store_true');a=p.parse_args();freeze() if a.freeze else run(a.pilot)

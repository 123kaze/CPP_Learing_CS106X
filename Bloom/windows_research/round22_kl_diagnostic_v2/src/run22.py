"""Launch only after round21_v2 completion or an explicit stopped/failed release.

No polling, no automatic retries; smoke is required before the 12 remaining cases.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from control22 import ROOT, digest, save, protocol, verify_freeze, serial_gate
import argparse
import csv
import fcntl
import json
import subprocess
import time
import uuid

THREAD_ENV = ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS')


def main(a):
    # Exactly one prior-completion read, before any data load, candidate work or timing.
    gate = serial_gate(release=a.release_marker)
    freeze = verify_freeze()
    cfg = protocol()
    results = ROOT/'results'
    results.mkdir(exist_ok=True)
    with (results/'run.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another round22 runner is active; refusing concurrent launch')
        outdir = results/a.stage
        if outdir.exists():
            raise FileExistsError('No retry/resume/overwrite permitted: '+str(outdir))
        smoke_index = cfg['smoke_case_index']
        cases = [smoke_index] if a.stage=='smoke' else [i for i in range(len(cfg['matrix'])) if i!=smoke_index]
        prior=[]
        smoke_link=None
        if a.stage=='matrix':
            smoke = results/'smoke/completion.json'
            sr=json.loads(smoke.read_text())
            if not (sr['status']=='complete' and sr['source_freeze_sha256']==freeze and sr['heuristic']==a.heuristic):
                raise RuntimeError('Require successful identical-protocol/flag smoke before matrix')
            for path,h in sr['worker_sha256'].items():
                p=ROOT/path
                if digest(p)!=h:raise RuntimeError('Verified smoke output changed')
                w=json.loads(p.read_text())
                if w['status']!='complete' or [r['case_index'] for r in w['cases']]!=[smoke_index]:
                    raise RuntimeError('Smoke cases do not match protocol')
                prior.extend(w['cases'])
            smoke_link=dict(path=str(smoke),sha256=digest(smoke))
        outdir.mkdir()
        env=os.environ.copy()
        for key in THREAD_ENV:env[key]='1'
        env['PYTHONDONTWRITEBYTECODE']='1'
        env['NUMBA_CACHE_DIR']=str(ROOT/'runtime_cache/numba')
        env['MPLCONFIGDIR']=str(ROOT/'runtime_cache/matplotlib')
        env['TMPDIR']=str(ROOT/'runtime_cache/tmp')
        for name in ('numba','matplotlib','tmp'):(ROOT/'runtime_cache'/name).mkdir(parents=True,exist_ok=True)
        token=uuid.uuid4().hex
        env['ROUND22_RUN_TOKEN']=token
        ticket=dict(status='authorized',token=token,case_indexes=cases,heuristic=a.heuristic,
                    source_freeze_sha256=freeze,serial_gate=gate,smoke_reference=smoke_link)
        ticket_path=outdir/'ticket.json';save(ticket_path,ticket)
        record=dict(status='running',stage=a.stage,heuristic=a.heuristic,source_freeze_sha256=freeze,
                    serial_gate=gate,smoke_reference=smoke_link,worker_sha256={},expected_new_cases=len(cases))
        manifest=outdir/'completion.json'
        save(manifest,record)
        started=time.perf_counter()
        combined=prior.copy()
        try:
            datasets=list(dict.fromkeys(cfg['matrix'][i]['dataset'] for i in cases))
            for ds in datasets:
                path=outdir/(ds+'.json');log=outdir/(ds+'.log')
                print('ROUND22 START',a.stage,ds,'one worker, one thread',flush=True)
                with log.open('x') as f:
                    proc=subprocess.run([sys.executable,'-I','-B','-u',str(ROOT/'src/worker22.py'),
                                         '--dataset',ds,'--ticket',str(ticket_path),'--output',str(path)],
                                        stdout=f,stderr=subprocess.STDOUT,env=env,cwd=ROOT)
                if proc.returncode!=0:
                    raise RuntimeError(f'Worker {ds} failed (exit {proc.returncode}); inspect {log}; no auto-retry')
                worker=json.loads(path.read_text())
                expect=[i for i in cases if cfg['matrix'][i]['dataset']==ds]
                if worker['status']!='complete' or [c['case_index'] for c in worker['cases']]!=expect:
                    raise RuntimeError('Worker incomplete or wrong matrix: '+ds)
                record['worker_sha256'][str(path.relative_to(ROOT))]=digest(path)
                combined.extend(worker['cases'])
                save(manifest,record)
                print('ROUND22 COMPLETE',ds,len(worker['cases']),'cases',flush=True)
            combined.sort(key=lambda r:r['case_index'])
            expected=[smoke_index] if a.stage=='smoke' else list(range(len(cfg['matrix'])))
            if [r['case_index'] for r in combined]!=expected:
                raise RuntimeError('Combined matrix mismatch')
            # Flat measurement tables for later inspection; no plots or tuning here.
            fieldnames=['case_index','dataset','budget_kib','workload','method','trees','frac','cache_bytes','FP','hits']
            with (outdir/'methods.csv').open('x',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fieldnames);writer.writeheader()
                for c in combined:
                    for method,result in c['methods'].items():
                        writer.writerow(dict(case_index=c['case_index'],dataset=c['dataset'],budget_kib=c['budget_kib'],
                            workload=c['workload'],method=method,trees=result['identity']['trees'],frac=result['identity']['frac'],
                            cache_bytes=result['identity']['cache_bytes'],FP=result['tail']['fp'],hits=result['tail']['hits']))
            static_fields=['case_index','dataset','budget_kib','workload','family','trees','pred_relaxed_FP',
                           'pred_capped_FP','pred_integer_FP','actual_tail_FP','interior_legal','KL',
                           'same_W_plain_proxy','raw_KL_says_win','capped_same_W_says_win','extra_cost_delta']
            with (outdir/'static_layers.csv').open('x',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=static_fields);writer.writeheader()
                for c in combined:
                    for r in c['static_candidates']:
                        t=r['A_B_available_budget']
                        writer.writerow(dict(case_index=c['case_index'],dataset=c['dataset'],budget_kib=c['budget_kib'],
                            workload=c['workload'],family=r['family'],trees=r['identity']['trees'],pred_relaxed_FP=t['relaxed_FP'],
                            pred_capped_FP=t['capped_FP'],pred_integer_FP=r['predicted_integer_FP'],actual_tail_FP=r['actual_tail_FP'],
                            **{k:t.get(k) for k in ('interior_legal','KL','same_W_plain_proxy','raw_KL_says_win',
                                                  'capped_same_W_says_win','extra_cost_delta')}))
            verify_freeze()
            record.update(status='complete',new_cases=len(cases),total_cases_in_tables=len(combined),
                          wall_s=time.perf_counter()-started)
            save(manifest,record)
        except BaseException as exc:
            record.update(status='failed',error=repr(exc),wall_s=time.perf_counter()-started)
            save(manifest,record)
            raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('stage',choices=('smoke','matrix'))
    p.add_argument('--heuristic',action='store_true',help='Explicitly deploy/evaluate the exploratory capped-KL+EB static13 selector')
    p.add_argument('--release-marker',type=Path,help='Coordinator-authored failed/stopped attestation within round22; never generated automatically')
    main(p.parse_args())

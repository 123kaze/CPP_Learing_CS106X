"""Sequential final phase, after heavy batch queues; never changes research/."""
import json,time,sys,subprocess,hashlib,datetime,platform,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/'results'/'final-phase.json'
def save(value):
    tmp=STATUS.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(STATUS)
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024**2),b''):h.update(chunk)
    return h.hexdigest()
def job(label,args):
    marker=ROOT/'results'/f'{label}.done'
    if marker.exists():return
    save(dict(stage=label,status='running',args=args));print('FINAL PHASE',label,flush=True)
    log=ROOT/'results'/f'{label}.log'
    if log.exists():log.replace(ROOT/'evidence'/f'{label}-previous-{time.time_ns()}.log')
    with log.open('w',encoding='utf-8') as f:
        r=subprocess.run([sys.executable,'-u',*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:
        save(dict(stage=label,status='failed',returncode=r.returncode,log=str(log)));raise RuntimeError(log)
    marker.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat(),encoding='utf-8')
def freeze():
    excluded={'summarize_main.py','build_report.py','make_figures.py','verify_round2.py'}
    files=[p for p in (ROOT/'src').glob('*') if p.suffix in ('.py','.cpp') and p.name not in excluded]
    files+=[ROOT/'plan'/'experiment-protocol.md',ROOT/'plan'/'clarifications.md']
    expected={str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in sorted(files)}
    path=ROOT/'plan'/'final-holdout-freeze.json'
    if path.exists():
        old=json.loads(path.read_text(encoding='utf-8'));assert old['operational_source_sha256']==expected,'Frozen operational sources changed'
    else:
        # This gate prohibits any pre-existing training or evaluation of2022.
        assert not (ROOT/'cache'/'mawi2022_flow'/'model200.txt').exists()
        payload=dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,
            platform=platform.platform(),operational_source_sha256=expected,
            holdout_source_metadata={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'data').glob('mawi2022-*json')},
            fixed_dataset='mawi2022_flow',budgets_kib=[16,24,32],learning_fraction=.25,
            note='First training/scoring/evaluation follows this operational code/protocol freeze. Reporting-only scripts excluded. One fixed source prefix, no outcome-based retry or tuning.')
        path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    return expected
def main():
    while True:
        queues=all((ROOT/'results'/f'queue-{name}.done').exists() for name in ('ablations','stacked_a','stacked_b','aqf'))
        strengthened=all(json.loads(p.read_text(encoding='utf-8')).get('zero_fallback_rechecked') for p in (ROOT/'results'/'stacked').glob('*/*.json'))
        hashes=all((ROOT/'results'/'hash_sensitivity'/f'{ds}.json').exists() and json.loads((ROOT/'results'/'hash_sensitivity'/f'{ds}.json').read_text(encoding='utf-8'))['completed'] for ds in ('caida_flow','mawi2021_flow'))
        if queues and strengthened and hashes:break
        save(dict(stage='waiting_for_heavy_queues',queues_complete=queues,stacked_strengthened=strengthened,hash_sensitivity_complete=hashes));time.sleep(10)
    job('A1-common-window',['src/repair_learning_window.py'])
    # Stop only the suite-owned monitor, after checking its exact command line.
    command="Get-CimInstance Win32_Process -Filter 'ProcessId=26772' | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'src[\\\\/]memory_monitor.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId }"
    subprocess.run(['powershell','-NoProfile','-Command',command],check=True,capture_output=True)
    (ROOT/'evidence'/'TIMING_ACTIVE').write_text('heavy batch queues finished; sequential benchmarks',encoding='utf-8')
    job('final-component-regression',['src/test_live_pipeline.py'])
    job('live-cod',['src/live_pipeline.py','--dataset','cod','--budgets','256,1024'])
    job('live-caida',['src/live_pipeline.py','--dataset','caida','--budgets','128,256'])
    job('real-sqlite',['src/run_sqlite_backend.py'])
    job('dynamic-insertion',['src/run_dynamic.py'])
    frozen=freeze()
    job('holdout-prepare',['src/prepare_datasets.py','mawi2022_flow'])
    job('holdout-main',['src/run_main.py','--dataset','mawi2022_flow','--budgets','16,24,32'])
    job('holdout-stacked',['src/run_stacked.py','--dataset','mawi2022_flow','--budgets','16,24,32'])
    job('holdout-aqf-preflight',['src/aqf_preflight.py','mawi2022_flow'])
    assert freeze()==frozen
    job('final-tables',['src/summarize_main.py'])
    save(dict(stage='experiments_and_tables_finished',status='passed',requires='Final integrity/result verification, report and figure QA'))
    (ROOT/'results'/'EXPERIMENTS_COMPLETE.json').write_text(json.dumps(dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),operational_freeze_unchanged=True),indent=2),encoding='utf-8')
if __name__=='__main__':main()

"""Serial audit then affected-case rechecks. Never writes into a frozen output root."""
from entry19 import *
import subprocess
import time
import platform
DATASETS=('caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow','mawi2024_flow','cod','url','caida','shalla')


def job(script,args,out):
    if out.exists():
        r=json.loads(out.read_text());assert r['status']=='complete' and r.get('exit_code')==0 and 'process_wall_s' in r,('Partial/failed result',out)
        return r
    log=out.with_suffix('.log');assert not log.exists(),('Partial log; no automatic retry',log)
    print('START',out.stem,flush=True);t=time.perf_counter()
    with log.open('x') as f:p=subprocess.run([sys.executable,'-u',str(ROOT/'src'/script),*args],stdout=f,stderr=subprocess.STDOUT)
    r=json.loads(out.read_text()) if out.exists() else dict(status='error',error=f'worker exit {p.returncode}')
    r.update(exit_code=p.returncode,process_wall_s=time.perf_counter()-t);save(out,r)
    if p.returncode or r['status']!='complete':
        print('FAILED',out.name,'\n',log.read_text()[-4500:],flush=True);raise SystemExit(1)
    print('COMPLETE',out.stem,f'{r["process_wall_s"]:.1f}s',flush=True)
    return r


def main():
    check_frozen();freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in freeze['inputs'].items():assert digest(BLOOM/rel)==h,rel
    manifest=dict(freeze=freeze,repair='Retain c only for gt=True,2<=c<=5,N[c]>0,N[c+1]=0',python=sys.version,platform=platform.platform())
    p=ROOT/'results/manifest.json'
    if p.exists():assert json.loads(p.read_text())==manifest,'Environment/source/input changed'
    else:save(p,manifest)
    streams=[]
    for ds in DATASETS:
        r=job('audit19.py',['--dataset',ds],ROOT/f'results/audit_{ds}.json');streams+=r['streams']
    main=[r for r in streams if r['cohort']=='main'];hold=[r for r in streams if r['cohort']=='holdout']
    main_cases=sum(len(r['budgets']) for r in main);changed=sum(len(r['budgets']) for r in main if not r['rate_bit_equal'])
    assert main_cases==1146 and changed==14
    assert len(streams)==325 and sum(len(r['budgets']) for r in hold)==4 and all(r['rate_bit_equal'] for r in hold)
    ex=job('audit19.py',['--dataset','extras'],ROOT/'results/audit_extras.json')
    save(ROOT/'results/audit_completion.json',dict(status='complete',main_cases=1146,changed_main_cases=14,
         unchanged_main_cases=1132,holdout_cases=4,unchanged_holdout_cases=4,extra_inputs=len(ex['streams']),changed_extras=ex['changed']))
    if ex['changed']:print('ADDITIONAL AFFECTED INPUTS REQUIRE FOLLOW-UP:',ex['changed'],flush=True)
    count=0
    for ds in ('cod','url','caida','shalla'):
        for mode in ('index','fp64'):
            r=job('rerun19.py',['--dataset',ds,'--cache',mode],ROOT/f'results/rerun_{ds}_{mode}.json')
            count+=len(r['cases'])
    assert count==28
    check_frozen()
    save(ROOT/'results/completion.json',dict(status='complete' if not ex['changed'] else 'affected_main_complete_extra_followup_required',
         changed_main_cases=14,cache_specific_rechecks=28,main_statistics_unchanged=1132,unchanged_holdout_cases=4,
         changed_extras=ex['changed'],manifest_sha256=digest(p)))
    print('ROUND19 FINISHED:14 affected cases rechecked in both cache formats; extra affected inputs:',len(ex['changed']),flush=True)


if __name__=='__main__':main()

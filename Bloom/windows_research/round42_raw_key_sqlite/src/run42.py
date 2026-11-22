import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker42 import ROOT,BLOOM,W,check
import subprocess,time,json,shutil


def launch(name,args):
    t=time.perf_counter();log=ROOT/f'results/{name}.log'
    with log.open('x') as f:subprocess.run([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdout=f,stderr=subprocess.STDOUT,timeout=1200,check=True)
    print('STAGE_COMPLETE',name,round(time.perf_counter()-t,3),flush=True)


def main():
    check();assert json.loads((ROOT.parent/'round41_exact_key_budget/results/verification.json').read_text())['status']=='verified';start=time.perf_counter()
    assert not (ROOT/'results/completion.json').exists()
    try:
        launch('final_unit_checks',['test42.py']);launch('pilot',['worker42.py','3601','--pilot'])
        p=json.loads((ROOT/'results/pilot.json').read_text());assert p['status']=='complete' and len(p['timings'])==7
        query=sum(r['elapsed_ns']/1e9 for r in p['timings'])
        # 9 cases x3 repetitions; separately reserve repeated setup and representative learning.
        predicted=query*(200000/p['queries'])*27+max(0,p['wall_s']-query)*9+180
        passed=predicted<=1800 and p['peak_rss_bytes']<4*1024**3 and shutil.disk_usage(BLOOM).free>=2*1024**3
        W.save(ROOT/'results/pilot_gate.json',dict(passed=passed,predicted_formal_s=predicted,limit_s=1800,pilot_query_s=query,pilot_wall_s=p['wall_s'],peak_rss_bytes=p['peak_rss_bytes'],method_outcomes_not_gate=True))
        assert passed,'Resource/time gate failed; preserve pilot, do not resize matrix'
        for seed in (3601,3602,3603):launch(f'seed{seed}',['worker42.py',str(seed)])
        launch('report',['report42.py']);check()
        W.save(ROOT/'results/completion.json',dict(status='complete',wall_s=time.perf_counter()-start));print('ROUND42_COMPLETE',flush=True)
    except BaseException as e:W.save(ROOT/'results/failure.json',dict(status='failed',error=repr(e),wall_s=time.perf_counter()-start));raise

if __name__=='__main__':main()

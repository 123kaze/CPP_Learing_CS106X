import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from catalog43 import *
import subprocess,shutil


def launch(name,args):
    log=ROOT/f'results/{name}.log';t=time.perf_counter()
    with log.open('x') as f:subprocess.run([sys.executable,'-I','-u',str(ROOT/'src'/args[0]),*args[1:]],cwd=BLOOM,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
    print('STAGE_COMPLETE',name,round(time.perf_counter()-t,3),flush=True)


def main():
    check();start=time.perf_counter();assert not (ROOT/'results/completion.json').exists()
    try:
        launch('final_unit_checks',['test43.py']);launch('pilot',['worker43.py','0','4301','--pilot'])
        pilot=json.loads((ROOT/'results/pilot.json').read_text());assert pilot['status']=='complete'
        case=pilot['cases'][0];query_s=sum(r['elapsed_ns']/1e9 for r in case['timings'])
        # All remaining pilot work repeated54times is deliberately conservative (includes setup).
        prediction=query_s*10*3*54+(pilot['wall_s']-query_s)*54+120
        passed=prediction<=3600 and pilot['peak_rss_bytes']<4*1024**3 and shutil.disk_usage(BLOOM).free>=2*1024**3
        W.save(ROOT/'results/pilot_gate.json',dict(passed=passed,predicted_formal_s=prediction,limit_s=3600,pilot_query_s=query_s,pilot_wall_s=pilot['wall_s'],peak_rss_bytes=pilot['peak_rss_bytes'],no_performance_or_AUC_gate=True))
        assert passed,'Pilot resource/time gate failed; matrix unchanged'
        for a in STRENGTHS:
            for seed in SEEDS:launch(f'a{a}_s{seed}',['worker43.py',str(a),str(seed)])
        launch('report',['report43.py']);check()
        W.save(ROOT/'results/completion.json',dict(status='complete',wall_s=time.perf_counter()-start));print('ROUND43_COMPLETE',flush=True)
    except BaseException as e:W.save(ROOT/'results/failure.json',dict(status='failed',error=repr(e),wall_s=time.perf_counter()-start));raise

if __name__=='__main__':main()

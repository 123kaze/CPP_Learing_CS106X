"""Resume COD and launch Caida once enough RAM is free; timing stays later."""
import sys,time,json,subprocess
from pathlib import Path
from queue_ablations import available
ROOT=Path(__file__).resolve().parents[1]
def completed(ds):
    p=ROOT/'results'/'ablations'/f'{ds}.json'
    return p.exists() and json.loads(p.read_text(encoding='utf-8'))['completed']
def main():
    child=None;log=None
    while not completed('cod') or not completed('caida'):
        if not completed('caida') and child is None and available()>=11*1024**3:
            log=(ROOT/'results'/'ablation-caida.log').open('w',encoding='utf-8')
            child=subprocess.Popen([sys.executable,'-u','src/run_ablation.py','--dataset','caida'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if child is not None and child.poll() is not None and child.returncode:raise RuntimeError('Caida ablation failed')
        (ROOT/'results'/'queue-ablations.json').write_text(json.dumps([dict(dataset=ds,status='passed' if completed(ds) else 'running' if ds=='cod' or child else 'waiting_for_RAM') for ds in ('cod','caida')],indent=2),encoding='utf-8')
        time.sleep(10)
    if child:child.wait()
    if log:log.close()
    for ds,kib in [('cod',256),('caida',128)]:
        with (ROOT/'results'/f'recalibration-{ds}.log').open('w',encoding='utf-8') as f:
            subprocess.run([sys.executable,'-u','src/run_recalibration.py','--dataset',ds,'--budget',str(kib)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    (ROOT/'results'/'queue-ablations.done').write_text('completed',encoding='utf-8')
if __name__=='__main__':main()

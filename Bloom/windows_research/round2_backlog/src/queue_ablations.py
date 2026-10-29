import time,json,subprocess,sys,ctypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Memory(ctypes.Structure):
    _fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong)]+[(s,ctypes.c_ulonglong) for s in ('ullTotalPhys','ullAvailPhys','ullTotalPageFile','ullAvailPageFile','ullTotalVirtual','ullAvailVirtual','ullAvailExtendedVirtual')]
def available():
    m=Memory();m.dwLength=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.ullAvailPhys
def main():
    jobs=[]
    for ds,need in [('cod',6*1024**3),('caida',9*1024**3)]:
        while available()<need:time.sleep(10)
        log=ROOT/'results'/f'ablation-{ds}.log';row=dict(dataset=ds,status='running');jobs.append(row)
        (ROOT/'results'/'queue-ablations.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
        with log.open('w',encoding='utf-8') as f:r=subprocess.run([sys.executable,'-u','src/run_ablation.py','--dataset',ds],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        row['status']='passed' if r.returncode==0 else 'failed';(ROOT/'results'/'queue-ablations.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
        if r.returncode:raise RuntimeError(log)
    for ds,kib in [('cod',256),('caida',128)]:
        with (ROOT/'results'/f'recalibration-{ds}.log').open('w',encoding='utf-8') as f:
            r=subprocess.run([sys.executable,'-u','src/run_recalibration.py','--dataset',ds,'--budget',str(kib)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(ds)
    (ROOT/'results'/'queue-ablations.done').write_text('completed',encoding='utf-8')
if __name__=='__main__':main()

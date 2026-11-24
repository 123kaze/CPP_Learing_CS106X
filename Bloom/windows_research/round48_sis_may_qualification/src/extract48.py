"""Only extract the preselected May file under explicit user-authorized resource limits."""
from pathlib import Path
import subprocess,hashlib,json,time,shutil,stat,resource
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent
FILE='sis-log-201805-anonymous.txt';EXPECTED_SIZE=13687894566;EXPECTED_MD5='dee4c55d036d6d1768a6f26a15b834c4'
MAX_OUTPUT=16*1024**3;MAX_RSS=4*1024**3;MIN_FREE=8*1024**3;TIMEOUT=1200


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');tmp.replace(p)

def check():
    freeze=json.loads((ROOT/'plan/extract-freeze.json').read_text())
    for section in ('sources','inputs'):
        for p,h in freeze[section].items():assert sha(BLOOM/p)==h,p

def limit_child():
    resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_OUTPUT,MAX_OUTPUT))


def main():
    check();start=time.perf_counter();folder=ROOT/'cache/may';folder.mkdir(parents=True,exist_ok=False);target=folder/FILE
    assert shutil.disk_usage(ROOT).free>EXPECTED_SIZE+MIN_FREE
    archive=WR/'round47_sis_acquisition_v2/inputs/archive_assembled/sis-log.zpaq';tool=WR/'round47_sis_acquisition/tools/executable/zpaq'
    download=json.loads((WR/'round47_sis_acquisition_v2/results/downloads.json').read_text());receipt=json.loads((WR/'round47_sis_acquisition/results/tool.json').read_text())
    assert download['status']=='verified' and archive.stat().st_size==2995604801 and sha(archive)==download['sha256']
    assert sha(tool)==receipt['binary_sha256']
    command=[str(tool),'extract',str(archive),FILE,'-to',str(target),'-threads','1','-noattributes']
    peak=0;proc=None
    with (ROOT/'results/extraction_stdout.log').open('x') as out,(ROOT/'results/extraction_stderr.log').open('x') as err:
        try:
            proc=subprocess.Popen(command,cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=out,stderr=err,preexec_fn=limit_child)
            while proc.poll() is None:
                elapsed=time.perf_counter()-start
                if elapsed>TIMEOUT:raise TimeoutError('Predeclared extraction wall limit')
                if shutil.disk_usage(ROOT).free<MIN_FREE:raise RuntimeError('Disk reserve limit')
                ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=5)
                if ps.returncode==0 and ps.stdout.strip():
                    rss=int(ps.stdout.strip())*1024;peak=max(peak,rss)
                    if rss>MAX_RSS:raise MemoryError('ExtractionRSSlimit; no automatic restart')
                if target.exists():
                    if not stat.S_ISREG(target.lstat().st_mode) or target.stat().st_size>MAX_OUTPUT:raise RuntimeError('Output type/size limit')
                time.sleep(.5)
            assert proc.returncode==0,f'Extractor exit{proc.returncode}'
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
    assert list(folder.iterdir())==[target] and target.stat().st_size==EXPECTED_SIZE
    md5=hashlib.md5();h=hashlib.sha256()
    with target.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):md5.update(block);h.update(block)
    assert md5.hexdigest()==EXPECTED_MD5
    check();save(ROOT/'results/extraction.json',dict(status='verified',filename=FILE,bytes=EXPECTED_SIZE,md5=md5.hexdigest(),sha256=h.hexdigest(),wall_s=time.perf_counter()-start,observed_peak_rss_bytes=peak,threads=1,max_output_bytes=MAX_OUTPUT,other_months_extracted=False,raw_HTTP_records_parsed=False,local_compilation=False));print('MAY_EXTRACTION_VERIFIED',EXPECTED_SIZE,flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as e:save(ROOT/'results/extraction_failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),no_automatic_retry=True));raise

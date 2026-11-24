from pathlib import Path
import subprocess,hashlib,json,time,shutil,stat,resource
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent
FILE='sis-log-201805-anonymous.txt';EXPECTED_SIZE=13687894566;EXPECTED_MD5='dee4c55d036d6d1768a6f26a15b834c4'
MAX_OUTPUT=16*1024**3;MAX_RSS=4*1024**3;MIN_FREE=8*1024**3;TIMEOUT=28800;THREADS=4


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');tmp.replace(p)

def check():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in freeze[group].items():assert sha(BLOOM/p)==h,p

def command(tool,archive,name,target):return [str(tool),'extract',str(archive),name,'-to',str(target),'-threads',str(THREADS),'-noattributes','-summary','1']

def limit_child():resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_OUTPUT,MAX_OUTPUT))

def sizes(target):
    if not target.exists():return dict(logical_bytes=0,allocated_bytes=0)
    st=target.lstat();assert stat.S_ISREG(st.st_mode),'Unexpectedoutputtype'
    return dict(logical_bytes=st.st_size,allocated_bytes=st.st_blocks*512)


def main():
    check();start=time.perf_counter();folder=ROOT/'cache/may';folder.mkdir(parents=True,exist_ok=False);target=folder/FILE
    assert shutil.disk_usage(ROOT).free>EXPECTED_SIZE+MIN_FREE
    archive=WR/'round47_sis_acquisition_v2/inputs/archive_assembled/sis-log.zpaq';tool=WR/'round47_sis_acquisition/tools/executable/zpaq'
    download=json.loads((WR/'round47_sis_acquisition_v2/results/downloads.json').read_text());toolmeta=json.loads((WR/'round47_sis_acquisition/results/tool.json').read_text())
    assert download['status']=='verified' and sha(archive)==download['sha256'];assert sha(tool)==toolmeta['binary_sha256']
    peak=0;proc=None;last=0.;elapsed=0.
    try:
        with (ROOT/'results/extraction_stdout.log').open('x') as out,(ROOT/'results/extraction_stderr.log').open('x') as err:
            try:
                proc=subprocess.Popen(command(tool,archive,FILE,target),cwd=BLOOM,stdin=subprocess.DEVNULL,stdout=out,stderr=err,preexec_fn=limit_child)
                save(ROOT/'results/start.json',dict(status='extracting',threads=THREADS,timeout_s=TIMEOUT,old_partial_reused=False));print('MAY_EXTRACTION_STARTED',THREADS,'threads',TIMEOUT,'seconds',flush=True)
                while proc.poll() is None:
                    elapsed=time.perf_counter()-start
                    if elapsed>TIMEOUT:raise TimeoutError('Userauthorized8hourlimit')
                    free=shutil.disk_usage(ROOT).free
                    if free<MIN_FREE:raise RuntimeError('Diskreserve limit')
                    ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=5)
                    if ps.returncode==0 and ps.stdout.strip():
                        rss=int(ps.stdout.strip())*1024;peak=max(peak,rss)
                        if rss>MAX_RSS:raise MemoryError('RSSlimit; no automatic restart')
                    state=sizes(target)
                    if state['logical_bytes']>MAX_OUTPUT:raise RuntimeError('Outputlimit')
                    if elapsed-last>=30:
                        save(ROOT/'results/progress.json',dict(status='extracting_unverified',wall_s=elapsed,observed_peak_rss_bytes=peak,free_disk_bytes=free,**state));last=elapsed
                    time.sleep(1)
                assert proc.returncode==0,f'Extractorexit{proc.returncode}'
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
        check();save(ROOT/'results/extraction.json',dict(status='verified',filename=FILE,bytes=EXPECTED_SIZE,md5=md5.hexdigest(),sha256=h.hexdigest(),wall_s=time.perf_counter()-start,observed_peak_rss_bytes=peak,threads=THREADS,max_output_bytes=MAX_OUTPUT,other_months_extracted=False,old_partial_reused=False,raw_HTTP_records_parsed=False,local_compilation=False));print('MAY_EXTRACTION_VERIFIED',EXPECTED_SIZE,flush=True)
    except BaseException as e:
        save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e),wall_s=time.perf_counter()-start,observed_peak_rss_bytes=peak,partial=sizes(target),no_automatic_retry=True));raise

if __name__=='__main__':main()

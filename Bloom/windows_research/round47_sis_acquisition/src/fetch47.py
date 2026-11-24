"""Bounded public data transfer; retain failed chunks, never parse partial archives."""
from pathlib import Path
import sys,json,re,hashlib,subprocess,time,shutil
from concurrent.futures import ThreadPoolExecutor,as_completed
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bootstrap47 import ROOT,BLOOM,sha,save,check
URL='https://zenodo.org/api/records/3241445/files/sis-log.zpaq/content'
TOTAL=2995604801;EXPECTED_MD5='8a48f22d0df19fb8d5044e54b66aac6e';PROBE=4*1024**2


def ranges(size=TOTAL,n=4):
    chunk=(size+n-1)//n
    return [(i*chunk,min(size,(i+1)*chunk)-1) for i in range(n)]


def verified_range(headers,lo,hi,total):
    # Redirect response blocks may precede the final206 block.
    responses=re.findall(r'(?im)^HTTP/\S+\s+(\d+)',headers)
    values=re.findall(r'(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)\s*$',headers.replace('\r',''))
    return bool(responses and responses[-1]=='206' and values and tuple(map(int,values[-1]))==(lo,hi,total))


def one(name,lo,hi,timeout):
    folder=ROOT/'inputs'/name;folder.mkdir(parents=True,exist_ok=False);target=folder/'payload.part';header=folder/'headers.txt';start=time.perf_counter()
    with (folder/'curl.log').open('x') as log:
        result=subprocess.run(['curl','--disable','--silent','--show-error','--fail','--location','--proto','=https','--proto-redir','=https','--connect-timeout','30','--max-time',str(timeout),'--max-filesize',str(hi-lo+1),'--range',f'{lo}-{hi}','--dump-header',str(header),'--output',str(target),'--write-out','%{http_code} %{size_download} %{time_starttransfer} %{time_total}',URL],stdout=subprocess.PIPE,stderr=log,text=True,timeout=timeout+15)
    row=dict(part=name,start=lo,end=hi,expected_bytes=hi-lo+1,exit_code=result.returncode,status='unverified',wall_s=time.perf_counter()-start,curl_metrics=result.stdout.strip())
    save(ROOT/f'results/{name}.json',row)
    assert result.returncode==0,'Range download failed; retain partial bytes; no retry'
    assert verified_range(header.read_text(),lo,hi,TOTAL),'Missing/mismatched206Content-Range'
    assert target.stat().st_size==hi-lo+1
    metrics=result.stdout.strip().split();assert len(metrics)==4 and metrics[0]=='206' and int(float(metrics[1]))==hi-lo+1
    row.update(status='verified',bytes=target.stat().st_size,sha256=sha(target),time_starttransfer_s=float(metrics[2]),time_total_s=float(metrics[3]))
    save(ROOT/f'results/{name}.json',row);print('RANGE_VERIFIED',name,row['bytes'],round(row['wall_s'],3),flush=True);return row


def main():
    check();start=time.perf_counter();assert shutil.disk_usage(ROOT).free>=24*1024**3
    assert not (ROOT/'results/downloads.json').exists()
    probe=one('network_probe',0,PROBE-1,120)
    # Estimate body transfer at measuredsingle-probe throughput; include4connection starts.
    body=max(.001,probe['time_total_s']-probe['time_starttransfer_s'])
    projected=TOTAL/PROBE*body+4*probe['time_starttransfer_s']
    passed=projected<=1800
    save(ROOT/'results/network_gate.json',dict(passed=passed,projected_full_transfer_s=projected,limit_s=1800,probe_bytes=PROBE,body_s=body,formula='total/probe_bytes*body_s+4*starttransfer_s; no4xparallel speed assumption'))
    assert passed,'Network gate failed; no large download launched; no automatic extension'
    jobs=ranges();rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        future={pool.submit(one,f'archive_part{i}',lo,hi,1200):i for i,(lo,hi) in enumerate(jobs)}
        for job in as_completed(future):rows.append(job.result())
    rows.sort(key=lambda r:r['start']);assert len(rows)==4
    folder=ROOT/'inputs/archive_assembled';folder.mkdir(parents=True,exist_ok=False);archive=folder/'sis-log.zpaq';md5=hashlib.md5();h=hashlib.sha256();total=0
    with archive.open('xb') as out:
        for row in rows:
            p=ROOT/f'inputs/{row["part"]}/payload.part';assert sha(p)==row['sha256']
            with p.open('rb') as f:
                while True:
                    data=f.read(1<<20)
                    if not data:break
                    out.write(data);md5.update(data);h.update(data);total+=len(data)
    assert total==TOTAL and md5.hexdigest()==EXPECTED_MD5
    check();save(ROOT/'results/downloads.json',dict(status='verified',url=URL,bytes=total,md5=md5.hexdigest(),sha256=h.hexdigest(),parts=rows,wall_s=time.perf_counter()-start,license='CC-BY-4.0',partial_data_used=False));print('ARCHIVE_DOWNLOAD_VERIFIED',total,flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as e:save(ROOT/'results/download_failure.json',dict(status='failed',error=repr(e)));raise

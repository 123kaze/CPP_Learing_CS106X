"""Explicitly user-authorized6hour resource variant; scientific inputs unchanged."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];OLD=ROOT.parent/'round47_sis_acquisition'
sys.path.insert(0,str(OLD/'src'))
import fetch47 as F
import json,hashlib,time,shutil
from concurrent.futures import ThreadPoolExecutor,as_completed


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in f[group].items():assert F.sha(BLOOM/p)==h,p


def main():
    check();start=time.perf_counter();assert not (ROOT/'results/downloads.json').exists();assert shutil.disk_usage(ROOT).free>=24*1024**3
    tool=json.loads((OLD/'results/tool.json').read_text());assert tool['status']=='verified' and F.sha(OLD/'tools/executable/zpaq')==tool['binary_sha256']
    gate=json.loads((OLD/'results/network_gate.json').read_text());assert not gate['passed'] and gate['projected_full_transfer_s']<=21600
    F.save(ROOT/'results/start.json',dict(status='downloading',wall_limit_s=21600,part_limit_s=20000,concurrency=4,user_authorized_longer_resource_limit=True,original_gate_kept=True,data_and_month_selection_unchanged=True))
    print('FOUR_RANGE_DOWNLOAD_STARTED',F.TOTAL,'bytes; max21600seconds; no retries',flush=True)
    previous=F.ROOT;F.ROOT=ROOT
    try:
        rows=[]
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs=[pool.submit(F.one,f'archive_part{i}',lo,hi,20000) for i,(lo,hi) in enumerate(F.ranges())]
            for job in as_completed(jobs):
                rows.append(job.result());F.save(ROOT/'results/progress.json',dict(status='downloading',verified_parts=len(rows),verified_bytes=sum(r['bytes'] for r in rows),wall_s=time.perf_counter()-start))
        assert time.perf_counter()-start<21600,'Authorizedoverall deadline exceeded'
        rows.sort(key=lambda r:r['start']);assert len(rows)==4
        folder=ROOT/'inputs/archive_assembled';folder.mkdir(parents=True,exist_ok=False);archive=folder/'sis-log.zpaq';md5=hashlib.md5();sha=hashlib.sha256();total=0
        with archive.open('xb') as out:
            for row in rows:
                p=ROOT/f'inputs/{row["part"]}/payload.part';assert F.sha(p)==row['sha256']
                with p.open('rb') as f:
                    while True:
                        block=f.read(1<<20)
                        if not block:break
                        out.write(block);md5.update(block);sha.update(block);total+=len(block)
        assert total==F.TOTAL and md5.hexdigest()==F.EXPECTED_MD5
        assert time.perf_counter()-start<21600
        check();F.save(ROOT/'results/downloads.json',dict(status='verified',bytes=total,md5=md5.hexdigest(),sha256=sha.hexdigest(),url=F.URL,parts=rows,wall_s=time.perf_counter()-start,partial_used=False));print('ARCHIVE_DOWNLOAD_VERIFIED',total,round(time.perf_counter()-start,3),flush=True)
    finally:F.ROOT=previous

if __name__=='__main__':
    try:main()
    except BaseException as e:F.save(ROOT/'results/failure.json',dict(status='failed',error=repr(e),no_automatic_retry=True));raise

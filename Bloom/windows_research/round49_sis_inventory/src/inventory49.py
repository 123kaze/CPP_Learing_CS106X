"""One complete immutable-file inventory; no model or method performance search."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent
sys.path.insert(0,str(WR/'round36_http_qualification/src'))
import data36 as HTTP
import sqlite3,json,hashlib,time,resource,shutil
SQL='INSERT INTO keys(k,flags,first_seen,last_seen,successes,misses) VALUES(?,?,?,?,?,?) ON CONFLICT(k) DO UPDATE SET flags=keys.flags|excluded.flags,last_seen=excluded.last_seen,successes=keys.successes+excluded.successes,misses=keys.misses+excluded.misses'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n');tmp.replace(p)

def check():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in freeze[group].items():assert sha(BLOOM/p)==h,p


def database(path):
    con=sqlite3.connect(path)
    con.execute('PRAGMA journal_mode=OFF');con.execute('PRAGMA synchronous=OFF');con.execute('PRAGMA cache_size=-65536');con.execute('PRAGMA mmap_size=0')
    con.execute('CREATE TABLE keys(k BLOB PRIMARY KEY,flags INTEGER NOT NULL,first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL,successes INTEGER NOT NULL,misses INTEGER NOT NULL) WITHOUT ROWID')
    return con


def aggregate(con):
    row=con.execute('SELECT coalesce(sum(flags=1),0),coalesce(sum(flags=2),0),coalesce(sum(flags=3),0),coalesce(sum(CASE WHEN flags=2 THEN misses ELSE 0 END),0),coalesce(sum(CASE WHEN flags=3 THEN misses ELSE 0 END),0),coalesce(sum(CASE WHEN flags=1 THEN successes ELSE 0 END),0),count(*) FROM keys').fetchone()
    return dict(zip(('members','negative_keys','conflicting_keys','retained_404_requests','conflicting_404_requests','retained_success_requests','distinct_keys'),map(int,row)))


def flush(con,batch):
    if batch:
        con.executemany(SQL,((key,*value) for key,value in batch.items()));con.commit();batch.clear()


def add(batch,key,label,ordinal):
    if key not in batch:batch[key]=[label,ordinal,ordinal,int(label==1),int(label==2)]
    else:
        row=batch[key];row[0]|=label;row[2]=ordinal;row[3]+=int(label==1);row[4]+=int(label==2)


def main():
    check();start=time.perf_counter();assert not (ROOT/'results/completion.json').exists()
    source=WR/'round48_sis_extract_v2/cache/may/sis-log-201805-anonymous.txt';receipt=json.loads((WR/'round48_sis_extract_v2/results/extraction.json').read_text());assert receipt['status']=='verified' and source.stat().st_size==receipt['bytes']
    cache=ROOT/'cache';cache.mkdir(exist_ok=False);db=cache/'inventory.sqlite';assert shutil.disk_usage(ROOT).free>=8*1024**3
    con=database(db);batch={};lines=parsed=backwards=bytecount=0;status={};skipped={};daily={};previous=minimum=maximum=None;digest=hashlib.sha256();last_update=0.;peak=0
    try:
        with source.open('rb') as f:
            while True:
                line=f.readline(65537)
                if not line:break
                assert len(line)<=65536,'Record limit';lines+=1;bytecount+=len(line);digest.update(line)
                item,reason=HTTP.decode_line(line)
                if item is None:skipped[reason]=skipped.get(reason,0)+1
                else:
                    stamp,key,code,fmt=item;ordinal=parsed;parsed+=1;s=str(code);status[s]=status.get(s,0)+1
                    day=stamp.date().isoformat();counts=daily.setdefault(day,{});counts[s]=counts.get(s,0)+1
                    if previous is not None and stamp<previous:backwards+=1
                    previous=stamp;minimum=stamp if minimum is None else min(minimum,stamp);maximum=stamp if maximum is None else max(maximum,stamp)
                    if code in (200,304,404):add(batch,key,2 if code==404 else 1,ordinal)
                if lines%10000==0:
                    flush(con,batch);elapsed=time.perf_counter()-start;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;peak=max(peak,rss)
                    assert elapsed<1800,'Inventory1800sdeadline; no automatic restart'
                    assert rss<=4*1024**3,'InventoryRSSlimit; no automatic restart'
                    assert db.stat().st_size<=8*1024**3 and shutil.disk_usage(ROOT).free>=8*1024**3,'Inventorydisklimit'
                    if elapsed-last_update>=30:
                        save(ROOT/'results/progress.json',dict(status='incomplete_inventory',raw_lines=lines,parsed_GET=parsed,input_bytes=bytecount,wall_s=elapsed,peak_rss_bytes=peak,db_bytes=db.stat().st_size));last_update=elapsed
                if lines==2000000:
                    flush(con,batch);ref=json.loads((WR/'round48_sis_may_qualification/results/data.json').read_text());got=aggregate(con)
                    assert parsed==ref['parsed_GET'] and status==ref['status_counts'] and bytecount==ref['prefix_bytes_read'] and digest.hexdigest()==ref['prefix_sha256']
                    for field in ('members','negative_keys','conflicting_keys','retained_404_requests','conflicting_404_requests','retained_success_requests'):assert got[field]==ref[field],field
                    save(ROOT/'results/prefix_regression.json',dict(status='verified',raw_lines=lines,parsed_GET=parsed,source_prefix_sha256=digest.hexdigest(),**got,old_round48_eligibility_not_changed=True));print('OLD_PREFIX_COUNTS_REPRODUCED',flush=True)
        flush(con,batch);assert bytecount==receipt['bytes'] and digest.hexdigest()==receipt['sha256'],'Full May file identity mismatch'
        counts=aggregate(con);retention=counts['retained_404_requests']/status.get('404',1)
        reasons=[]
        for field,limit in (('members',10000),('negative_keys',1000),('retained_404_requests',10000)):
            if counts[field]<limit:reasons.append(f'{field}<{limit}')
        if retention<.9:reasons.append('404retention<.9')
        # Fixed coarse frequency bins, complete catalogue; no model-dependent grouping.
        hist={}
        for label,flag in (('member',1),('negative',2),('conflict',3)):
            result=con.execute("SELECT CASE WHEN successes+misses=1 THEN '1' WHEN successes+misses<=5 THEN '2-5' WHEN successes+misses<=20 THEN '6-20' WHEN successes+misses<=100 THEN '21-100' ELSE '101+' END,count(*),sum(successes+misses) FROM keys WHERE flags=? GROUP BY 1",(flag,)).fetchall()
            hist[label]=[dict(frequency_bin=k,keys=n,requests=q) for k,n,q in result]
        meta=dict(status='complete',exploratory_after_prefix_audit=True,independent_holdout=False,raw_lines=lines,parsed_GET=parsed,source_bytes=bytecount,source_sha256=digest.hexdigest(),status_counts=status,skipped=skipped,minimum_timestamp=minimum.isoformat(),maximum_timestamp=maximum.isoformat(),time_reversals=backwards,daily_GET_status_counts=daily,**counts,retained_404_fraction=retention,basic_fullfile_scale_passes=not reasons,basic_scale_failure_reasons=reasons,full_method_qualification_done=False,model_AUC_measured=False,method_FP_measured=False,frequency_bins=hist,db_bytes=db.stat().st_size,db_sha256=None,wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        con.close();con=None;meta['db_sha256']=sha(db);check();save(ROOT/'results/inventory.json',meta);save(ROOT/'results/completion.json',dict(status='complete',wall_s=time.perf_counter()-start,basic_scale_passes=not reasons,not_method_qualification=True));print('FULL_MAY_INVENTORY_COMPLETE',counts['members'],counts['negative_keys'],counts['retained_404_requests'],flush=True)
    except BaseException as e:save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300],raw_lines=lines,parsed_GET=parsed,wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,no_automatic_retry=True));raise
    finally:
        if con is not None:con.close()

if __name__=='__main__':main()

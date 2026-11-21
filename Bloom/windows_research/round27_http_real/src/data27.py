"""Parse untrusted HTTP logs as data; never import from the input directories."""
import os
for _v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_v]='1'
import array
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
import numpy as np

FEATURES=['bytes','slash','dot','digit','uppercase','dash','underscore','percent','question','ampersand','equals','tilde','max_component','trailing_slash','html','gif','jpeg','txt','cgi','document']
LINE=re.compile(rb'^\S+\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"GET (\S+)(?: HTTP/[^\"]+)?"\s+(\d{3})\s+')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n');tmp.replace(path)


def lexical(key):
    path=key.split(b'?',1)[0].lower()
    return [len(key),key.count(b'/'),key.count(b'.'),sum(48<=c<=57 for c in key),sum(65<=c<=90 for c in key),
            *[key.count(c) for c in (b'-',b'_',b'%',b'?',b'&',b'=',b'~')],max(map(len,key.split(b'/')),default=0),
            path.endswith(b'/'),path.endswith((b'.html',b'.htm')),path.endswith(b'.gif'),path.endswith((b'.jpg',b'.jpeg')),
            path.endswith(b'.txt'),path.endswith(b'.cgi'),path.endswith((b'.ps',b'.pdf'))]


def parse(source,destination):
    destination=Path(destination);assert not destination.exists(),'Refuse prepared-data overwrite'
    start=time.perf_counter();keys={};flags=[];first=[];targets=[];record_key=array.array('q');record_status=array.array('B');record_order=array.array('q')
    total=parsed=0;status_counts={};time_reversals=0;prev=None;first_stamp=last_stamp=None
    with gzip.open(source,'rb') as f:
        for line in f:
            total+=1;m=LINE.match(line)
            if not m:continue
            stamp,target,status=m.groups();status=int(status);order=parsed;parsed+=1
            status_counts[status]=status_counts.get(status,0)+1
            # Month is constant within each selected source; no client identities retained.
            clock=(int(stamp[:2]),stamp[12:20])
            if prev is not None and clock<prev:time_reversals+=1
            prev=clock
            if first_stamp is None:first_stamp=stamp.decode('ascii',errors='replace')
            last_stamp=stamp.decode('ascii',errors='replace')
            if status not in (200,304,404):continue
            if target not in keys:
                keys[target]=len(targets);targets.append(target);flags.append(0);first.append(order)
            k=keys[target];flag=2 if status==404 else 1;flags[k]|=flag
            record_key.append(k);record_status.append(flag);record_order.append(order)
    flag=np.asarray(flags,np.uint8);keep=flag!=3;idx=np.flatnonzero(keep);mapping=np.full(len(flags),-1,np.int64);mapping[idx]=np.arange(len(idx))
    rk=np.asarray(record_key,np.int64);ro=np.asarray(record_order,np.int64);rs=np.asarray(record_status,np.uint8);good=keep[rk]
    ids=np.array([int.from_bytes(hashlib.sha256(targets[i]).digest()[:8],'little') for i in idx],np.uint64)
    assert len(np.unique(ids))==len(ids),'Resource identity hash collision: refuse silently merging keys'
    X=np.asarray([lexical(targets[i]) for i in idx],np.float32);y=flag[idx]==1
    assert X.shape==(len(ids),len(FEATURES)) and y.any() and (~y).any()
    destination.parent.mkdir(parents=True,exist_ok=True)
    np.savez(destination,ids=ids,y=y,X=X,first=np.asarray(first,np.int64)[idx],trace=mapping[rk[good]],order=ro[good],boundary=np.int64(parsed//4),features=np.asarray(FEATURES))
    meta=dict(source_file=Path(source).name,source_sha256=sha(source),prepared_sha256=sha(destination),
              lines=total,parsed_GET=parsed,unparsed_or_nonGET=total-parsed,status_counts=status_counts,
              first_timestamp=first_stamp,last_timestamp=last_stamp,recorded_order_time_reversals=time_reversals,
              stable_keys=len(ids),members=int(y.sum()),negatives=int((~y).sum()),conflicting_keys=int((flag==3).sum()),
              conflicting_success_requests=int(((~good)&(rs==1)).sum()),conflicting_404_requests=int(((~good)&(rs==2)).sum()),
              retained_success_requests=int((good&(rs==1)).sum()),retained_404_requests=int((good&(rs==2)).sum()),
              boundary_GET_ordinal=parsed//4,parse_feature_seconds=time.perf_counter()-start,
              construction='retrospective stable subset; catalog/conflict exclusions use entire month; recorded order retained',features=FEATURES)
    save(destination.with_suffix('.json'),meta)
    print(json.dumps(meta,ensure_ascii=False),flush=True)
    return meta


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path);a=p.parse_args();parse(a.source,a.destination)

"""Fixed first2million raw lines: observed HTTP response classes, never business existence claims."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round36_http_qualification/src'))
import data36 as HTTP
sys.path.insert(0,str(WR/'round41_exact_key_budget/src'))
import exact41 as E
from exact41 import W,E5,np,pack
import json,hashlib,array,time,resource
SEEDS=(4801,4802,4803);MAX_LINES=2000000


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,x):return W.save(Path(p),x)

def check():
    frozen=json.loads((ROOT/'plan/qualification-freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in frozen[group].items():assert sha(BLOOM/p)==h,p


def path_prefix(key,depth):
    path=key.split(b'?',1)[0];parts=[p for p in path.split(b'/') if p]
    return b'/'.join(parts[:depth])


def stable_arrays(keys,flags,first,record_key,record_order,record_flag,get_count):
    flags=np.asarray(flags,np.uint8);keep=flags!=3;idx=np.flatnonzero(keep);mapping=np.full(len(keys),-1,np.int64);mapping[idx]=np.arange(len(idx))
    rk=np.asarray(record_key,np.int64);ro=np.asarray(record_order,np.int64);rf=np.asarray(record_flag,np.uint8);good=keep[rk];names=[keys[i] for i in idx]
    ids=np.array([int.from_bytes(hashlib.sha256(k).digest()[:8],'little') for k in names],np.uint64);assert len(np.unique(ids))==len(ids),'Finite keyID collision'
    X=np.asarray([HTTP.lexical(k) for k in names],np.float32).reshape(-1,20);y=flags[idx]==1;blob,offsets=pack(names)
    arrays=dict(ids=ids,y=y,X=X,first=np.asarray(first,np.int64)[idx],trace=mapping[rk[good]],order=ro[good],boundary=np.int64(get_count//4),blob=blob,offsets=offsets,features=np.array(HTTP.FEATURES))
    stats=dict(conflicting_keys=int((flags==3).sum()),conflicting_404_requests=int((~good&(rf==2)).sum()),retained_404_requests=int((good&(rf==2)).sum()),retained_success_requests=int((good&(rf==1)).sum()))
    rules={}
    for depth in (1,2):
        supports=sorted({path_prefix(k,depth) for k,yes in zip(names,y) if yes});bs,os=pack(supports);support_set=set(supports)
        reject=np.array([path_prefix(k,depth) not in support_set for k in names],np.bool_);assert not reject[y].any()
        arrays[f'prefix{depth}_reject']=reject
        rules[str(depth)]=dict(support_entries=len(supports),packed_support_payload_bytes=bs.nbytes+os.nbytes,packed_support_array_bytes=sys.getsizeof(bs)+sys.getsizeof(os),negative_distinct_rejected=int(reject[~y].sum()),negative_requests_rejected=int(reject[arrays['trace']][~y[arrays['trace']]].sum()),storage_scope='packed byte/offset arrays, not Python sets or measured online implementation')
    return arrays,stats,rules


def parse():
    check();start=time.perf_counter();extract_root=WR/'round48_sis_extract_v2';source=extract_root/'cache/may/sis-log-201805-anonymous.txt';extraction=json.loads((extract_root/'results/extraction.json').read_text());assert extraction['status']=='verified' and source.stat().st_size==extraction['bytes']
    dest=ROOT/'cache/sis_may_prefix.npz';assert not dest.exists()
    keys=[];mapping={};flags=[];first=[];rk=array.array('q');ro=array.array('q');rf=array.array('B');status={};skipped={};formats={};lines=parsed=backwards=bytes_read=0
    minimum=maximum=previous=None;prefixhash=hashlib.sha256();eof=False
    with source.open('rb') as f:
        for _ in range(MAX_LINES):
            line=f.readline(65537)
            if not line:eof=True;break
            assert len(line)<=65536,'Record larger than64KiB';lines+=1;bytes_read+=len(line);prefixhash.update(line)
            item,reason=HTTP.decode_line(line)
            if item is None:skipped[reason]=skipped.get(reason,0)+1;continue
            stamp,target,code,fmt=item;ordinal=parsed;parsed+=1;status[str(code)]=status.get(str(code),0)+1;formats[fmt]=formats.get(fmt,0)+1
            if previous is not None and stamp<previous:backwards+=1
            previous=stamp;minimum=stamp if minimum is None else min(minimum,stamp);maximum=stamp if maximum is None else max(maximum,stamp)
            if code not in (200,304,404):continue
            i=mapping.get(target)
            if i is None:i=len(keys);mapping[target]=i;keys.append(target);flags.append(0);first.append(ordinal)
            label=2 if code==404 else 1;flags[i]|=label;rk.append(i);ro.append(ordinal);rf.append(label)
    assert parsed>0,'No parsedGET requests'
    arrays,counts,rules=stable_arrays(keys,flags,first,rk,ro,rf,parsed)
    np.savez_compressed(dest,**arrays);y=arrays['y'];trace=arrays['trace'];order=arrays['order'];bound=int(arrays['boundary'])
    original404=status.get('404',0);meta=dict(status='complete',raw_line_limit=MAX_LINES,raw_lines=lines,reached_EOF=eof,prefix_bytes_read=bytes_read,prefix_sha256=prefixhash.hexdigest(),full_may_md5=extraction['md5'],parsed_GET=parsed,status_counts=status,skipped=skipped,timestamp_formats=formats,time_reversals=backwards,minimum_timestamp=minimum.isoformat(),maximum_timestamp=maximum.isoformat(),members=int(y.sum()),negative_keys=int((~y).sum()),**counts,retained_404_fraction=counts['retained_404_requests']/original404 if original404 else 0.,member_catalog_uses_full_selected_prefix=True,whole_month_analyzed=False,business_record_existence_not_inferred=True,cheap_rules=rules,learning_raw_members=int(y[trace[order<bound]].sum()),learning_raw_negatives=int((~y[trace[order<bound]]).sum()),tail_raw_members=int(y[trace[order>=bound]].sum()),tail_raw_negatives=int((~y[trace[order>=bound]]).sum()),feature_payload_bytes=arrays['X'].nbytes,raw_key_payload_bytes=arrays['blob'].nbytes,prepared_sha256=sha(dest),wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    assert meta['peak_rss_bytes']<=4*1024**3,'Parser RSS cap; no automatic restart'
    save(ROOT/'results/data.json',meta);check();print('MAY_PREFIX_PARSED',meta['members'],meta['negative_keys'],meta['retained_404_requests'],flush=True)
    return meta

if __name__=='__main__':
    try:parse()
    except Exception as e:save(ROOT/'results/parse_failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300]));raise

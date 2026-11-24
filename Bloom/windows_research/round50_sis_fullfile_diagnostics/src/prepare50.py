import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent
sys.path.insert(0,str(WR/'round48_sis_may_qualification/src'))
from data48 import HTTP,W,E5,np,path_prefix,pack
import sqlite3,json,hashlib,array,time,resource,shutil
SEEDS=(5001,5002,5003)


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,x):return W.save(Path(p),x)

def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for rel,h in f[group].items():assert sha(BLOOM/rel)==h,rel


def prepare():
    check();start=time.perf_counter();r49=WR/'round49_sis_inventory';inventory=json.loads((r49/'results/inventory.json').read_text());assert inventory['status']=='complete' and inventory['basic_fullfile_scale_passes']
    db=r49/'cache/inventory.sqlite';assert sha(db)==inventory['db_sha256'];folder=ROOT/'cache';folder.mkdir(exist_ok=False)
    t=time.perf_counter();con=sqlite3.connect(f'file:{db}?mode=ro',uri=True);con.execute('PRAGMA cache_size=-65536');con.execute('PRAGMA query_only=ON')
    n,rawbytes=con.execute('SELECT count(*),sum(length(k)) FROM keys WHERE flags IN(1,2)').fetchone();assert n==inventory['members']+inventory['negative_keys']
    ids=np.empty(n,np.uint64);y=np.empty(n,np.bool_);X=np.empty((n,20),np.float32);first=np.empty(n,np.int64);blob=np.empty(rawbytes,np.uint8);offsets=np.zeros(n+1,np.int64)
    negatives={};supports={1:set(),2:set()};at=0
    for i,(key,flag,seen) in enumerate(con.execute('SELECT k,flags,first_seen FROM keys WHERE flags IN(1,2) ORDER BY k')):
        ids[i]=int.from_bytes(hashlib.sha256(key).digest()[:8],'little');y[i]=flag==1;first[i]=seen;X[i]=HTTP.lexical(key)
        blob[at:at+len(key)]=np.frombuffer(key,np.uint8);at+=len(key);offsets[i+1]=at
        if flag==2:negatives[key]=i
        else:
            for depth in (1,2):supports[depth].add(path_prefix(key,depth))
        if i%100000==0:
            assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<=4*1024**3,'PreparationRSSlimit; no automatic restart'
            assert time.perf_counter()-start<1800,'Preparationdeadline'
    con.close();assert at==rawbytes and int(y.sum())==inventory['members'] and len(negatives)==inventory['negative_keys'];assert len(np.unique(ids))==n
    catalogue_s=time.perf_counter()-t
    t=time.perf_counter();source=WR/'round48_sis_extract_v2/cache/may/sis-log-201805-anonymous.txt';trace=array.array('q');order=array.array('q');lines=get_count=0;digest=hashlib.sha256()
    with source.open('rb') as f:
        while True:
            line=f.readline(65537)
            if not line:break
            assert len(line)<=65536;lines+=1;digest.update(line);item,_=HTTP.decode_line(line)
            if item is not None:
                _,key,code,_=item;ordinal=get_count;get_count+=1
                if code==404:
                    ix=negatives.get(key)
                    if ix is not None:trace.append(ix);order.append(ordinal)
            if lines%100000==0:assert time.perf_counter()-start<1800,'Preparationdeadline'
    assert lines==inventory['raw_lines'] and get_count==inventory['parsed_GET'] and digest.hexdigest()==inventory['source_sha256']
    trace=np.asarray(trace,np.int64);order=np.asarray(order,np.int64);assert len(trace)==inventory['retained_404_requests'] and not y[trace].any()
    trace_s=time.perf_counter()-t;rules={};rejects={}
    for depth in (1,2):
        neg_reject=np.array([path_prefix(key,depth) not in supports[depth] for key in negatives],np.bool_)
        # negatives insertion order is catalogue order, so its positions matchflatnonzero(~y).
        assert list(negatives.values())==np.flatnonzero(~y).tolist()
        reject=np.zeros(n,np.bool_);reject[~y]=neg_reject;rejects[f'prefix{depth}_reject']=reject
        pb,po=pack(sorted(supports[depth]));rules[str(depth)]=dict(entries=len(supports[depth]),packed_support_array_bytes=sys.getsizeof(pb)+sys.getsizeof(po),negative_distinct_rejected=int(neg_reject.sum()),negative_requests_rejected=int(reject[trace].sum()))
    target=folder/'sis_fullfile.npz';t=time.perf_counter()
    np.savez_compressed(target,ids=ids,y=y,X=X,first=first,negative_trace=trace,negative_order=order,boundary=np.int64(get_count//4),blob=blob,offsets=offsets,**rejects)
    assert target.stat().st_size<=4*1024**3 and shutil.disk_usage(ROOT).free>=8*1024**3
    meta=dict(status='complete',members=int(y.sum()),negative_keys=int((~y).sum()),negative_requests=len(trace),raw_lines=lines,GET_queries=get_count,boundary_GET=get_count//4,source_sha256=digest.hexdigest(),inventory_db_sha256=inventory['db_sha256'],prepared_sha256=sha(target),catalogue_prepare_s=catalogue_s,negative_trace_rescan_s=trace_s,write_and_hash_s=time.perf_counter()-t,feature_payload_bytes=X.nbytes,raw_key_payload_bytes=blob.nbytes,all_trace_is_negative=True,no_member_index_built=True,cheap_rules=rules,wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    assert meta['peak_rss_bytes']<=4*1024**3;save(ROOT/'results/preparation.json',meta);check();print('FULLFILE_PREPARATION_COMPLETE',n,len(trace),flush=True)


def load(seed):
    with np.load(ROOT/'cache/sis_fullfile.npz',allow_pickle=False) as d:ids,y,X,first,tr,order,boundary,p1,p2=[d[k] for k in ('ids','y','X','first','negative_trace','negative_order','boundary','prefix1_reject','prefix2_reject')]
    u=(E5.C.splitmix64(ids^np.uint64(seed))>>np.uint64(11)).astype(float)/2**53;early=first<int(boundary)
    sp=dict(member_train=y&(u<.5),neg_train=(~y)&early&(u<.1),neg_val=(~y)&early&(u>=.1)&(u<.2));sp['neg_test']=(~y)&~(sp['neg_train']|sp['neg_val'])
    pos=np.full(len(ids),-1,np.int64);pos[sp['neg_test']]=np.arange(sp['neg_test'].sum());q=pos[tr];learn=q[(q>=0)&(order<int(boundary))];tail=q[(q>=0)&(order>=int(boundary))]
    return ids,y,X,sp,learn,tail,(p1,p2)

if __name__=='__main__':
    try:prepare()
    except Exception as e:save(ROOT/'results/preparation_failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300]));raise

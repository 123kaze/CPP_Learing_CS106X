import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round44_trace_snapshot/src'))
import data44 as D
from data44 import W,np,sha,save
import gzip,hashlib,subprocess,json,csv,array,time,math,shutil,resource
URL='https://www.secrepo.com/maccdc2012/dns.log.gz';SIZE=6606969;SEEDS=(4601,4602,4603)


def normalize(q):
    if not q or q in (b'-',b'.') or b'\\x' in q or any(c<33 or c>126 for c in q):return None
    out=q.lower();out=out[:-1] if out.endswith(b'.') else out
    return out if out else None


def response(rcode,answers):
    if rcode==b'3':return 2
    if rcode==b'0' and answers not in (b'',b'-',b'(empty)'):return 1
    return 0


def features(key):
    parts=key.split(b'.');counts=np.bincount(np.frombuffer(key,np.uint8),minlength=256);p=counts[counts>0]/len(key);entropy=float(-(p*np.log2(p)).sum())
    return D.lexical(key)+[len(parts),max(map(len,parts)),sum(map(len,parts))/len(parts),entropy,key.endswith(b'.com'),key.endswith(b'.net'),key.endswith(b'.org'),any(p.startswith(b'xn--') for p in parts)]


def check():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in freeze['sources'].items():assert sha(BLOOM/rel)==h,rel


def fetch():
    folder=ROOT/'inputs/source';folder.mkdir(parents=True,exist_ok=False);p=folder/'dns.log.gz';start=time.perf_counter()
    with (folder/'curl.log').open('x') as f:
        result=subprocess.run(['curl','--fail','--location','--proto','=https','--proto-redir','=https','--connect-timeout','20','--max-time','120','--max-filesize',str(10*1024**2),'--header','If-Match: "64d079-503965768af73"','--dump-header',str(folder/'headers.txt'),'--output',str(p),URL],stdout=f,stderr=subprocess.STDOUT,timeout=140)
    receipt=dict(url=URL,status='downloaded_unverified',exit_code=result.returncode,seconds=time.perf_counter()-start,expected_bytes=SIZE)
    save(ROOT/'results/download.json',receipt);assert result.returncode==0 and p.stat().st_size==SIZE
    total=0;h=hashlib.sha256()
    with gzip.open(p,'rb') as f:
        while True:
            block=f.read(1<<20)
            if not block:break
            total+=len(block);assert total<=256*1024**2;h.update(block)
    receipt.update(status='verified',bytes=SIZE,sha256=sha(p),uncompressed_bytes=total,uncompressed_sha256=h.hexdigest(),gzip_crc_passed=True,seconds=time.perf_counter()-start)
    save(ROOT/'results/download.json',receipt);return p


def parse(path):
    start=time.perf_counter();positions=None;keys=[];mapping={};flags=[];first=[];rk=array.array('q');ro=array.array('q');rs=array.array('B')
    records=aqueries=accepted=unsupported=unknown=reverse=0;previous=minimum=maximum=None;rcodes={};expanded=0
    with gzip.open(path,'rb') as f:
        while True:
            line=f.readline(65537)
            if not line:break
            expanded+=len(line);assert len(line)<=65536 and expanded<=256*1024**2
            if line.startswith(b'#fields\t'):
                names=line.rstrip(b'\r\n').split(b'\t')[1:];positions={name:i for i,name in enumerate(names)}
                assert all(k in positions for k in (b'ts',b'query',b'qtype',b'rcode',b'answers'));continue
            if line.startswith(b'#') or not line.strip():continue
            assert positions is not None,'MissingZeek#fields';record=line.rstrip(b'\r\n').split(b'\t');assert len(record)==len(positions);records+=1
            if record[positions[b'qtype']]!=b'1':continue
            ordinal=aqueries;aqueries+=1;stamp=float(record[positions[b'ts']]);assert math.isfinite(stamp)
            if previous is not None and stamp<previous:reverse+=1
            previous=stamp;minimum=stamp if minimum is None else min(minimum,stamp);maximum=stamp if maximum is None else max(maximum,stamp)
            code=record[positions[b'rcode']];rcodes[code.decode('ascii')]=rcodes.get(code.decode('ascii'),0)+1
            key=normalize(record[positions[b'query']])
            if key is None:unsupported+=1;continue
            label=response(code,record[positions[b'answers']])
            if not label:unknown+=1;continue
            k=mapping.get(key)
            if k is None:k=len(keys);mapping[key]=k;keys.append(key);flags.append(0);first.append(ordinal)
            flags[k]|=label;rk.append(k);ro.append(ordinal);rs.append(label);accepted+=1
    assert aqueries>0
    flags=np.asarray(flags,np.uint8);keep=flags!=3;ix=np.flatnonzero(keep);mapnew=np.full(len(keys),-1,np.int64);mapnew[ix]=np.arange(len(ix))
    rk=np.asarray(rk,np.int64);ro=np.asarray(ro,np.int64);rs=np.asarray(rs,np.uint8);good=keep[rk];names=[keys[i] for i in ix]
    ids=np.array([int.from_bytes(hashlib.sha256(k).digest()[:8],'little') for k in names],np.uint64);assert len(np.unique(ids))==len(ids)
    X=np.asarray([features(k) for k in names],np.float32).reshape(-1,32);y=flags[ix]==1;blob,offsets=D.pack(names)
    out=ROOT/'cache/dns46.npz';assert not out.exists();out.parent.mkdir(exist_ok=True)
    np.savez_compressed(out,ids=ids,y=y,X=X,first=np.asarray(first,np.int64)[ix],trace=mapnew[rk[good]],order=ro[good],boundary=np.int64(aqueries//4),blob=blob,offsets=offsets)
    neg=int(((rs==2)&good).sum());orig=int((rs==2).sum())
    meta=dict(status='complete',records=records,A_queries=aqueries,rcode_counts=rcodes,unsupported_names=unsupported,excluded_response_types=unknown,members=int(y.sum()),negative_keys=int((~y).sum()),retained_NXDOMAIN_requests=neg,recognized_NXDOMAIN_requests=orig,all_A_NXDOMAIN_requests=rcodes.get('3',0),retained_NXDOMAIN_fraction=neg/rcodes['3'] if rcodes.get('3',0) else 0.,conflicting_names=int((flags==3).sum()),minimum_timestamp=minimum,maximum_timestamp=maximum,A_time_reversals=reverse,development_boundary_Aordinal=aqueries//4,prepared_sha256=sha(out),source_sha256=sha(path),parse_feature_s=time.perf_counter()-start,features=32,retrospective_stable_response_subset=True,production_DNS=False,task='observedAanswer/observedNXDOMAIN static retrospective subset from security competition capture')
    save(ROOT/'results/data.json',meta);return out,meta


def diagnose(path,meta):
    rows=[];reasons=[]
    for field,threshold in (('members',1000),('negative_keys',1000),('retained_NXDOMAIN_requests',10000)):
        if meta[field]<threshold:reasons.append(f'{field}<{threshold}')
    if meta['retained_NXDOMAIN_fraction']<.9:reasons.append('NXDOMAINretention<.9')
    for seed in SEEDS:
        start=time.perf_counter()
        with np.load(path,allow_pickle=False) as d:ids,y,X,first,trace,order,boundary=[d[k] for k in ('ids','y','X','first','trace','order','boundary')]
        u=(W.E5.C.splitmix64(ids^np.uint64(seed))>>np.uint64(11)).astype(float)/2**53;early=first<int(boundary)
        sp=dict(member_train=y&(u<.5),neg_train=(~y)&early&(u<.1),neg_val=(~y)&early&(u>=.1)&(u<.2));sp['neg_test']=(~y)&~(sp['neg_train']|sp['neg_val'])
        positions=np.full(len(ids),-1,np.int64);positions[sp['neg_test']]=np.arange(sp['neg_test'].sum());query=positions[trace]
        learn=query[(query>=0)&(order<int(boundary))];tail=query[(query>=0)&(order>=int(boundary))]
        from types import SimpleNamespace
        s=SimpleNamespace(y=y,h1q=np.empty(int(sp['neg_test'].sum()),np.uint64))
        row=dict(seed=seed,train_negative_keys=int(sp['neg_train'].sum()),validation_negative_keys=int(sp['neg_val'].sum()),learning_queries=len(learn),tail_queries=len(tail),development_auc16=None)
        for field,threshold in (('train_negative_keys',20),('validation_negative_keys',20),('learning_queries',1000),('tail_queries',1000)):
            if row[field]<threshold:reasons.append(f'seed{seed}:{field}<{threshold}')
        freq=np.bincount(learn,minlength=len(s.h1q));row['learning_repeat_fraction']=1-float((freq>0).sum())/len(learn) if len(learn) else 0.
        f=np.ascontiguousarray(X).view(np.dtype((np.void,32*4))).ravel();row['query_feature_overlap_fraction']=float(np.isin(f[sp['neg_test']],f[s.y]).mean()) if len(s.h1q) else 0.
        if sp['neg_train'].any() and sp['neg_val'].any() and sp['member_train'].any():
            train=sp['member_train']|sp['neg_train'];model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[train],label=s.y[train]),num_boost_round=16)
            scores=model.predict(X,raw_score=True,num_threads=1);held=(s.y&~sp['member_train'])|sp['neg_val'];row['development_auc16']=W.auc(s.y[held],scores[held]);cuts=np.unique(np.quantile(scores[sp['neg_val']],[.2,.4,.6,.8]));reg=np.searchsorted(cuts,scores[sp['neg_test']],side='right');regions=[]
            for g in range(len(cuts)+1):
                c=freq[reg==g];n=int(c.sum());d=int((c>0).sum());regions.append(dict(region=g,queries=n,distinct=d,repeat_fraction=1-d/n if n else None))
            rr=[r['repeat_fraction'] for r in regions if r['distinct']>=50 and r['repeat_fraction'] is not None];gap=max(rr)-min(rr) if len(rr)>=2 else None
            row.update(regions=regions,qualified_repeat_gap=gap,interesting_flag=bool(row['development_auc16']>=.7 and row['query_feature_overlap_fraction']>=.01 and row['learning_repeat_fraction']>=.1 and gap is not None and gap>=.1))
        row['wall_s']=time.perf_counter()-start;rows.append(row)
    save(ROOT/'results/qualification.json',dict(status='complete',eligible_for_methods=not reasons,reasons=reasons,diagnostics=rows,method_FP_not_evaluated=True,task=meta['task']))
    return not reasons


def main():
    check();assert shutil.disk_usage(ROOT).free>=2*1024**3;start=time.perf_counter();source=fetch();path,meta=parse(source);eligible=diagnose(path,meta);check()
    save(ROOT/'results/completion.json',dict(status='complete',eligible_for_methods=eligible,wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss));print('DNS_QUALIFICATION_COMPLETE',eligible,flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as e:save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300]));raise

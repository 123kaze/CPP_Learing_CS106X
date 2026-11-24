"""Treat downloaded request files as untrusted data; define an explicit prefix-only snapshot."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(ROOT/'src'))
from fetch44 import sha,save
sys.path.insert(0,str(WR/'round41_exact_key_budget/src'))
import exact41 as E
from exact41 import W,E5,B,RA,R6,np,pack
from types import SimpleNamespace
import re,csv,hashlib,json,time,array,resource,math
SEEDS=(4401,4402,4403);CLUSTERS=('cluster001','cluster002','cluster003')
FEATURES=('bytes','colon','slash','dot','underscore','dash','equals','percent','question','ampersand','digits','uppercase','lowercase','tokens','max_token','min_nonempty_token','leading_alpha','leading_digit','trailing_alpha','trailing_digit','first_digit','last_digit','alpha_fraction','digit_fraction')
TOKEN=re.compile(rb'[:/_\-.]')


def lexical(key):
    assert isinstance(key,bytes) and len(key)>0
    digit=lambda c:48<=c<=57
    alpha=lambda c:65<=c<=90 or 97<=c<=122
    def run(seq,pred):
        n=0
        for c in seq:
            if not pred(c):break
            n+=1
        return n
    tokens=TOKEN.split(key);nonempty=[len(t) for t in tokens if t]
    digits=sum(map(digit,key));upper=sum(65<=c<=90 for c in key);lower=sum(97<=c<=122 for c in key)
    return [len(key),*[key.count(c) for c in (b':',b'/',b'.',b'_',b'-',b'=',b'%',b'?',b'&')],digits,upper,lower,len(tokens),max(map(len,tokens)),min(nonempty) if nonempty else 0,run(key,alpha),run(key,digit),run(reversed(key),alpha),run(reversed(key),digit),int(digit(key[0])),int(digit(key[-1])),(upper+lower)/len(key),digits/len(key)]


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for rel,h in f.get(section,{}).items():assert sha(BLOOM/rel)==h,rel
    return sha(ROOT/'plan/freeze.json')


def decode(line):
    if len(line)>65536:raise ValueError('Record exceeds64KiB')
    row=next(csv.reader([line.decode('utf8')],strict=True))
    if len(row)!=7:raise ValueError('Expected exactly7CSV fields')
    stamp=float(row[0]);size=int(row[2]);int(row[3]);int(row[6])
    if not math.isfinite(stamp) or size<0:raise ValueError('Invalid timestamp or key size')
    key=row[1].encode('utf8');operation=row[5].strip().lower()
    if not key or b'\n'in key or b'\r'in key:raise ValueError('Empty/multilinekey forbidden')
    return stamp,key,size,operation


def assemble(keys,first,trace):
    trace=np.asarray(trace,np.int64);first=np.asarray(first,np.int64);n=len(trace);catalog_end=n//4;learn_end=n//2
    y=first<catalog_end
    ids=np.array([int.from_bytes(hashlib.sha256(k).digest()[:8],'little') for k in keys],np.uint64)
    assert len(np.unique(ids))==len(ids),'Finite compressedID collision; stop'
    X=np.asarray([lexical(k) for k in keys],np.float32);blob,offsets=pack(keys)
    assert X.shape==(len(ids),24)
    return dict(ids=ids,y=y,X=X,blob=blob,offsets=offsets,first=first,trace=trace,catalog_end=np.int64(catalog_end),learn_end=np.int64(learn_end),features=np.array(FEATURES))


def parse(cluster):
    check();start=time.perf_counter();dest=ROOT/f'cache/{cluster}.npz';assert not dest.exists()
    source=ROOT/f'inputs/{cluster}/trace.csv';download=json.loads((ROOT/'results/downloads.json').read_text());receipt=next(r for r in download['files'] if r['name']==cluster);assert receipt['status']=='verified' and sha(source)==receipt['sha256']
    seen={};keys=[];first=[];sizes=[];size_changed=set();trace=array.array('q');operations={};lines=backwards=0;previous=minimum=maximum=None
    with source.open('rb') as f:
        while True:
            line=f.readline(65537)
            if not line:break
            lines+=1
            if lines>2000000:raise ValueError('Exceeds2million records')
            try:stamp,key,size,op=decode(line)
            except Exception as err:raise ValueError(f'Invalid schema at record{lines}; exception={type(err).__name__}; rawcontents withheld') from None
            operations[op]=operations.get(op,0)+1
            if op not in ('get','gets'):continue
            if previous is not None and stamp<previous:backwards+=1
            previous=stamp;minimum=stamp if minimum is None else min(minimum,stamp);maximum=stamp if maximum is None else max(maximum,stamp)
            ix=seen.get(key)
            if ix is None:ix=len(keys);seen[key]=ix;keys.append(key);first.append(len(trace));sizes.append(size)
            elif sizes[ix]!=size:size_changed.add(ix)
            trace.append(ix)
    assert len(trace)>0
    arrays=assemble(keys,first,trace);dest.parent.mkdir(exist_ok=True);np.savez_compressed(dest,**arrays)
    y=arrays['y'];t=arrays['trace'];ce=int(arrays['catalog_end']);le=int(arrays['learn_end']);feat=arrays['X'].view(np.dtype((np.void,24*4))).ravel()
    meta=dict(status='complete',cluster=cluster,source_sha256=sha(source),prepared_sha256=sha(dest),lines=lines,operations=operations,GET_queries=len(t),keys=len(keys),members=int(y.sum()),distinct_negative_keys=int((~y).sum()),catalog_GET_boundary=ce,learning_GET_end=le,minimum_GET_timestamp=minimum,maximum_GET_timestamp=maximum,GET_time_reversals=backwards,original_key_size_changes=len(size_changed),raw_key_payload_bytes=arrays['blob'].nbytes,long_keys_over128=sum(len(k)>128 for k in keys),learning_raw_members=int(y[t[ce:le]].sum()),learning_raw_negatives=int((~y[t[ce:le]]).sum()),tail_raw_members=int(y[t[le:]].sum()),tail_raw_negatives=int((~y[t[le:]]).sum()),negative_keys_sharing_member_features=int(np.isin(feat[~y],feat[y]).sum()),member_catalog_uses_future=False,original_backend_NotFound_inferred=False,task='exact key membership in first25percentGET checkpoint; real-trace-driven constructed static dedup task',parse_feature_save_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save(ROOT/f'results/{cluster}_data.json',meta);check();print('PARSED',cluster,'members',meta['members'],'negative_keys',meta['distinct_negative_keys'],'seconds',meta['parse_feature_save_s'],flush=True)
    return meta


def prepare(path,seed):
    with np.load(path,allow_pickle=False) as d:ids,y,X,first,trace,ce,le=[d[k] for k in ('ids','y','X','first','trace','catalog_end','learn_end')]
    ce,le=int(ce),int(le);u=(E5.C.splitmix64(ids^np.uint64(seed))>>np.uint64(11)).astype(float)/2**53
    early=first<le;sp=dict(member_train=y&(u<.5),neg_train=(~y)&early&(u<.1),neg_val=(~y)&early&(u>=.1)&(u<.2));sp['neg_test']=(~y)&~(sp['neg_train']|sp['neg_val'])
    pos=np.full(len(ids),-1,np.int64);pos[sp['neg_test']]=np.arange(sp['neg_test'].sum());q=pos[trace]
    learn=q[ce:le];learn=learn[learn>=0];tail=q[le:];tail=tail[tail>=0]
    h=E5.C.splitmix64(ids^np.uint64(E5.C.H1_SALT)^np.uint64(seed))
    s=SimpleNamespace(name=f'{Path(path).stem}_{seed}',ids=ids,y=y,split=sp,h1m=h[y],h1q=h[sp['neg_test']],q_ids=ids[sp['neg_test']])
    assert not np.intersect1d(ids[sp['neg_train']|sp['neg_val']],s.q_ids).size
    assert np.array_equal(y,first<ce) and (first[sp['neg_train']|sp['neg_val']]>=ce).all() and (first[sp['neg_train']|sp['neg_val']]<le).all()
    return s,X,learn,tail


def budgets(n):return tuple(sorted({max(4,(int(n)*bits+8191)//8192) for bits in (2,4,8)}))

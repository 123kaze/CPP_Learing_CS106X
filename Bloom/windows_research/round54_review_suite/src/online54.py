"""Actual raw-key query path with calibrated local exact-key service substitute.
No precomputed membership labels, scores or flags enter online(). They are used
only outside timing to verify the returned masks and final exact-cache state.
"""
import sys,re,ctypes
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shared54 import *
LIB=ctypes.CDLL(None)
CLOCK=LIB.mach_absolute_time;CLOCK.argtypes=[];CLOCK.restype=ctypes.c_uint64
class Timebase(ctypes.Structure):_fields_=[('numer',ctypes.c_uint32),('denom',ctypes.c_uint32)]
TB=Timebase();assert LIB.mach_timebase_info(ctypes.byref(TB))==0
NANO_PER_TICK=TB.numer/TB.denom

@njit(cache=False)
def ticks():return CLOCK()
@njit(cache=False)
def spin_to(deadline):
    while CLOCK()<deadline:pass


def url_features(key):
    s=key.decode('utf-8');host=s.split('/',1)[0];tld=host.rsplit('.',1)[-1]
    return np.asarray([s.count('.'),s.count('www'),s.count('@'),s.count('/'),s.count('//'),s.count('https'),s.count('http'),s.count('%'),s.count('-'),s.count('='),len(s),len(host),len(tld),len(re.findall('[0-9]',s)),len(re.findall('[A-Za-z]',s)),bool(re.match(r'^\d{1,3}(?:\.\d{1,3}){3}',s)),len(re.findall('[aeiouAEIOU]',s)),host.count('.')+1],np.float32)


def identity_features(key,ds,seed,need_features):
    if ds in ('clark','sis'):
        ident=int.from_bytes(hashlib.sha256(key).digest()[:8],'little');x=np.asarray(O42.lexical(key),np.float32) if need_features else None
    elif ds=='url':
        s=key.decode('utf-8');ident=int(pd.util.hash_array(np.array([s],object),categorize=False)[0]);x=url_features(key) if need_features else None
    else:
        assert ds=='mawi2024_flow' and len(key)==9
        src=int.from_bytes(key[:4],'little');dst=int.from_bytes(key[4:8],'little');lab=int(key[8])
        ident=int(pd.util.hash_array(np.array([f'{src}>{dst}#{lab}'],object),categorize=False)[0]);x=np.array([src,dst],np.float32) if need_features else None
    h=np.uint64(O42.salted_hash(np.uint64(ident),seed))
    return h,x


class Filter:
    def __init__(self,d,c):
        self.d=d;self.c=c;st=c['structure'];self.spec=d.cache.layout(c['cache_bytes']);self.model=None;self.bf=None
        if c['trees']:
            td=E5.tree(d.s,d.scores,c['trees']);reg=E5.D.region_of_segment(st.b);arrays=E5.R._MODEL_ARRAYS[d.s.name,c['trees']]
            self.model=tuple(arrays[k] for k in ('feat','thr','left','right','leaf','roots'))
            edges=E5.D.edges()[st.b[1:-1]];self.cuts=np.log(edges)-np.log1p(-edges)
            self.off=np.concatenate([[0],np.cumsum(st.m)]).astype(np.int64);self.bits=np.zeros((int(self.off[-1])+7)//8,np.uint8)
            E5.R.packed_build(d.s.h1m,reg[td.seg_m].astype(np.int32),self.off,st.m,st.k,self.bits)
            self.kind,self.m,self.k=st.kind,st.m,st.k
            self.arrays=[*arrays.values(),self.cuts,self.kind,self.off,self.m,self.k,self.bits]
        else:self.bf=st.data;self.arrays=[self.bf]
        assert sum(sys.getsizeof(v) for v in self.arrays)+c['cache_bytes']<=st.used_bytes<=st.budget_bytes
        self.reset()
    def reset(self):self.data=self.d.cache.allocate(self.spec)
    def probe(self,key):
        h,_=identity_features(key,self.d.ds,self.d.seed,False);v=np.frombuffer(key,np.uint8)
        if K53.lookup(self.data,h,v,self.spec['buckets'],self.d.cache.width):return 2,h,v
        if self.model is not None:
            # Hash must not be recomputed when extracting features after a cache miss.
            if self.d.ds in ('clark','sis'):x=np.asarray(O42.lexical(key),np.float32)
            elif self.d.ds=='url':x=url_features(key)
            else:x=np.array([int.from_bytes(key[:4],'little'),int.from_bytes(key[4:8],'little')],np.float32)
            yes=O42.learned_probe(x,h,*self.model,self.cuts,self.kind,self.off,self.m,self.k,self.bits)
        else:yes=O42.bf_probe(h,self.bf)
        return int(yes),h,v
    def absent(self,h,v):return K53.insert(self.data,h,v,self.spec['buckets'],self.d.cache.width)


@njit(cache=True)
def batch_learned(X,hashes,model,cuts,kind,off,m,k,bits):
    out=np.zeros(len(hashes),np.bool_)
    for i in range(len(hashes)):out[i]=O42.learned_probe(X[i],hashes[i],*model,cuts,kind,off,m,k,bits)
    return out


@njit(cache=True)
def reference(requests,hashes,blob,offsets,flags,y,state,nb,width):
    mask=np.zeros(len(requests),np.uint8);found=np.zeros(len(requests),np.uint8)
    for j,i in enumerate(requests):
        key=blob[offsets[i]:offsets[i+1]];h=hashes[i]
        if K53.lookup(state,h,key,nb,width):assert not y[i];continue
        if not flags[i]:assert not y[i];continue
        mask[j]=1
        if y[i]:found[j]=1
        else:K53.insert(state,h,key,nb,width)
    return mask,found


class Backend:
    def __init__(self,members,target_us):self.members=members;self.target_us=target_us;self.value=b'v'*32
    def lookup(self,key):
        begin=ticks();exists=key in self.members;spin_to(np.uint64(begin+int(self.target_us*1000/NANO_PER_TICK)))
        return self.value if exists else None


def online(keys,flt,backend):
    mask=np.zeros(len(keys),np.uint8);found=np.zeros(len(keys),np.uint8);hits=0
    begin=time.perf_counter_ns()
    for j,key in enumerate(keys):
        decision,h,v=flt.probe(key) if flt else (1,None,None)
        if decision==2:hits+=1
        elif decision==1:
            mask[j]=1;value=backend.lookup(key)
            if value is not None:found[j]=1
            elif flt:flt.absent(h,v)
    elapsed=time.perf_counter_ns()-begin
    return dict(ns_per_query=elapsed/len(keys),elapsed_ns=elapsed,calls=int(mask.sum()),fp=int(mask.sum()-found.sum()),members_found=int(found.sum()),cache_hits=hits),mask,found


def mixture(d,p,N=5000):
    rng=np.random.default_rng(5401);nm=int(round(N*p));neg=d.qi[np.resize(d.tail,N-nm)]
    members=rng.choice(d.mi,nm,replace=True);requests=np.concatenate([members,neg]);order=rng.permutation(N)
    # Keep negative relative order, randomize only member positions.
    positions=np.sort(order[:nm]);out=np.empty(N,np.int64);is_m=np.zeros(N,np.bool_);is_m[positions]=True
    out[is_m]=members;out[~is_m]=neg
    assert int(d.s.y[out].sum())==nm
    return out


def run(ds):
    check();start=time.perf_counter();seed=5001 if ds=='sis' else 3601 if ds=='clark' else 0;d=load(ds,seed);kib=DMATRIX[ds]
    picks,aux=pick(d,kib);filters={};config=[];hashes=C.splitmix64(d.s.ids^np.uint64(C.H1_SALT)^np.uint64(seed))
    flags={};t=time.perf_counter()
    # Independently regenerate raw-key hashes and features, all input keys, once.
    for i in range(len(d.s.ids)):
        key=d.blob[d.off[i]:d.off[i+1]].tobytes();h,x=identity_features(key,ds,seed,True)
        assert h==hashes[i] and np.array_equal(x,d.X[i]),f'Raw hash/feature mismatch {ds} row {i}'
    raw_validation_s=time.perf_counter()-t
    for method in ('Gama','Replay','RAglobal','RA6','BF','PlainBF'):
        c,select_s=picks[method];t=time.perf_counter();flt=Filter(d,c);rebuild_s=time.perf_counter()-t;filters[method]=flt
        t=time.perf_counter()
        if c['trees']:f=batch_learned(d.X,hashes,flt.model,flt.cuts,flt.kind,flt.off,flt.m,flt.k,flt.bits)
        else:f=B.query_all(flt.bf,hashes)
        assert f[d.mi].all() and np.array_equal(f[d.qi],c['structure'].fp_static)
        flags[method]=f
        ix=int(d.qi[0]);key=d.blob[d.off[ix]:d.off[ix+1]].tobytes();_,h,v=flt.probe(key);flt.absent(h,v);flt.reset()
        learning=(d.meta['timings']['training_s'] or 0)+(d.meta['timings']['score_and_model_arrays_s'] or 0)+d.meta['timings']['tree_prepare_s'] if c['trees'] else 0.
        incremental=learning+select_s+rebuild_s
        config.append(dict(method=method,trees=c['trees'],selection_build_s=select_s,executable_rebuild_s=rebuild_s,validation_and_jit_s=time.perf_counter()-t,incremental_train_score_select_build_s=incremental,shared_input_load_s=d.meta['timings']['load_s'],shared_JIT_s=d.meta['timings']['jit_s'],full_training_measured=ds in ('clark','sis'),startup_scope=d.meta['training_scope'],**ledger(c)))
    filters['NoFilter']=None;flags['NoFilter']=np.ones(len(d.s.ids),np.bool_)
    t=time.perf_counter();members={d.blob[d.off[i]:d.off[i+1]].tobytes() for i in d.mi};assert len(members)==len(d.mi)
    backend_setup_s=time.perf_counter()-t;backend_bytes=sys.getsizeof(members)+sum(sys.getsizeof(k) for k in members)+sys.getsizeof(b'v'*32)
    del aux  # Selection workspace is not deployment memory.
    ticks();spin_to(np.uint64(ticks()+1));rows=[];calibration=[];methods=tuple(filters)
    ratios=(.1,.5,.9,.99,.9984) if ds=='sis' else (.1,.5,.9,.99)
    for target in (3,37,100):
        backend=Backend(members,target);mkey=next(iter(members));nkey=d.blob[d.off[d.qi[0]]:d.off[d.qi[0]+1]].tobytes();samples=[]
        for j in range(200):
            t=time.perf_counter_ns();backend.lookup(mkey if j%2 else nkey);samples.append((time.perf_counter_ns()-t)/1000)
        calibration.append(dict(target_us=target,median_actual_us=float(np.median(samples)),p05_us=float(np.quantile(samples,.05)),p95_us=float(np.quantile(samples,.95)),min_us=min(samples),max_us=max(samples)))
        for p in ratios:
            requests=mixture(d,p);keys=[d.blob[d.off[i]:d.off[i+1]].tobytes() for i in requests];refs={}
            for method,flt in filters.items():
                spec=flt.spec if flt else d.cache.layout(0);state=d.cache.allocate(spec)
                mask,found=reference(requests,hashes,d.blob,d.off,flags[method],d.s.y,state,spec['buckets'],d.cache.width)
                assert np.array_equal(found,d.s.y[requests].astype(np.uint8));refs[method]=(mask,found,ah(state))
            for rep in range(3):
                order=methods[rep:]+methods[:rep]
                if rep%2:order=order[::-1]
                for position,method in enumerate(order):
                    flt=filters[method]
                    if flt:flt.reset()
                    r,mask,found=online(keys,flt,backend);rm,rf,rs=refs[method]
                    assert np.array_equal(mask,rm) and np.array_equal(found,rf)
                    if flt:assert ah(flt.data)==rs
                    rows.append(dict(dataset=ds,budget_kib=kib,member_fraction=p,target_backend_us=target,rep=rep,position=position,method=method,queries=len(keys),member_fn=0,request_sha=ah(requests),accepted_sha=ah(mask),found_sha=ah(found),cache_sha=rs,**r))
            print('QUERY_CELL',ds,p,target,'complete',flush=True)
    out=dict(status='complete',meta=d.meta,configuration=config,calibration=calibration,rows=rows,raw_hash_and_feature_validation_s=raw_validation_s,backend_exact_set_build_s=backend_setup_s,backend_shared_physical_bytes=backend_bytes,backend='Local raw-key exact Python set with returned value/None and calibrated CPU delay; not SQLite/RPC/production',resampling='Uniform member keys, original negative tail order, randomized member positions; not original natural mixed traffic',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    assert len(rows)==(315 if ds=='sis' else 252);save(ROOT/f'results/online_{ds}.json',out);check()

if __name__=='__main__':run(sys.argv[1])

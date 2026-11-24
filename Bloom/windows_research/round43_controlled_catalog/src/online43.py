"""Measured raw8-byte-key SQL path; exact uint64 cache, no index or label input."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from catalog43 import *
from numba import njit
import sqlite3
EMPTY=np.empty(0,np.uint64)
SQL_METHODS=('NoFilter','BF+Cache','RA6','Replay');PROPORTIONS=(.1,.9)


@njit(cache=True)
def hash_key(key,seed):
    return E5.C.mix64((np.uint64(key)^np.uint64(seed)^np.uint64(E5.C.H1_SALT))+np.uint64(0x9E3779B97F4A7C15))


@njit(cache=True)
def probe_bf(key,seed,bf,data,nb,Q,ob,sb):
    h=hash_key(key,seed)
    if nb and F.lookup(data,h,nb,64,Q,ob,sb,4):return 2,h
    m,k=np.int64(bf[1]),np.int64(bf[2])
    for j in range(k):
        p=E5.C.bf_pos(h,j,m)
        if (bf[B.HEAD_WORDS+(p>>6)]>>np.uint64(p&63))&np.uint64(1)==0:return 0,h
    return 1,h


@njit(cache=True)
def probe_model(key,seed,feat,thr,left,right,leaf,roots,cuts,kind,off,m,k,bits,data,nb,Q,ob,sb):
    h=hash_key(key,seed)
    if nb and F.lookup(data,h,nb,64,Q,ob,sb,4):return 2,h
    x=np.float32(np.uint64(key)>>np.uint64(56))/np.float32(255)
    score=0.
    for root in roots:
        node=np.int64(root)
        while node>=0:
            assert feat[node]==0
            node=np.int64(left[node] if x<=thr[node] else right[node])
        score+=leaf[~node]
    g=np.searchsorted(cuts,score,side='left')
    if kind[g]==E5.C.PASS:return 1,h
    if kind[g]!=E5.C.BF:return 0,h
    for j in range(k[g]):
        p=off[g]+E5.C.bf_pos(h,j,m[g])
        if (bits[p>>3]>>np.uint64(p&7))&np.uint64(1)==0:return 0,h
    return 1,h


class Executable:
    def __init__(self,c,s,scores,seed):
        self.seed=seed;self.spec=F.layout(c['cache_bytes']);st=c['structure'];self.used=st.used_bytes;self.trees=c['trees']
        if self.trees:
            td=E5.tree(s,scores,self.trees);reg=E5.D.region_of_segment(st.b);arr=E5.R._MODEL_ARRAYS[s.name,self.trees]
            self.model=tuple(arr[k] for k in ('feat','thr','left','right','leaf','roots'))
            edges=E5.D.edges()[st.b[1:-1]];cuts=np.log(edges)-np.log1p(-edges)
            off=np.concatenate([[0],np.cumsum(st.m)]).astype(np.int64);bits=np.zeros(st.filter_bytes,np.uint8)
            E5.R.packed_build(s.h1m,reg[td.seg_m].astype(np.int32),off,st.m,st.k,bits)
            assert np.array_equal(E5.R.packed_query(s.h1q,st.q_region,st.kind,off,st.m,st.k,bits),st.fp_static)
            arrays=(*self.model,cuts,st.kind,off,st.m,st.k,bits);self.base=arrays;self.impl=probe_model
        else:self.base=(st.data,);arrays=self.base;self.impl=probe_bf
        assert all(a.flags.owndata for a in arrays)
        self.physical_array_bytes=sum(sys.getsizeof(a) for a in arrays)+c['cache_bytes'];assert self.physical_array_bytes<=self.used
        self.reset()
    def reset(self):
        p=self.spec;self.data=F.allocate(p) if p['buckets'] else EMPTY
        self.args=(*self.base,self.data,p['buckets'],p['Q'],p['ob'],p['slot_bits'])
    def probe(self,key):return self.impl(np.uint64(key),self.seed,*self.args)
    def absent(self,h):
        p=self.spec
        return F.insert(self.data,np.uint64(h),p['buckets'],64,p['Q'],p['ob'],p['slot_bits'],4,p['handbits']) if p['buckets'] else 0


@njit(cache=True)
def verify_static(keys,seed,impl,args):
    result=np.empty(len(keys),np.bool_)
    for i in range(len(keys)):decision,_=impl(keys[i],seed,*args);result[i]=decision==1
    return result


@njit(cache=True)
def reference(seq,hashes,member,flags,data,nb,Q,ob,sb,hb):
    accepted=np.zeros(len(seq),np.uint8);found=np.zeros(len(seq),np.uint8)
    for j,ix in enumerate(seq):
        x=np.int64(ix);h=hashes[x]
        if nb and F.lookup(data,h,nb,64,Q,ob,sb,4):assert not member[x];continue
        if not flags[x]:assert not member[x];continue
        accepted[j]=1
        if member[x]:found[j]=1
        elif nb:F.insert(data,h,nb,64,Q,ob,sb,4,hb)
    return accepted,found


def mixed(s,tail,seed,p,n=20000):
    rng=np.random.default_rng(seed+129000+int(p*10));mask=rng.random(n)<p
    out=np.empty(n,np.int64);mi=np.flatnonzero(s.y);qi=np.flatnonzero(s.split['neg_test'])
    out[mask]=rng.choice(mi,int(mask.sum()));out[~mask]=qi[tail[:int((~mask).sum())]]
    return out


def database(path,keys,y):
    t=time.perf_counter();con=sqlite3.connect(path)
    con.execute('PRAGMA journal_mode=OFF');con.execute('PRAGMA synchronous=OFF');con.execute('PRAGMA cache_size=-2048');con.execute('PRAGMA mmap_size=0')
    con.execute('CREATE TABLE kv(k BLOB PRIMARY KEY,v BLOB NOT NULL) WITHOUT ROWID')
    con.executemany('INSERT INTO kv VALUES(?,?)',((key,b'v'*32) for key,yes in zip(keys,y) if yes));con.commit();con.execute('PRAGMA query_only=ON')
    return con,dict(build_s=time.perf_counter()-t,file_bytes=Path(path).stat().st_size,page_count=con.execute('PRAGMA page_count').fetchone()[0],sqlite_version=sqlite3.sqlite_version)


def online(cur,keys,seq,flt,accepted,found):
    calls=fp=hit=members=0;t=time.perf_counter_ns()
    for j,ix in enumerate(seq):
        raw=keys[int(ix)]
        if flt is None:decision,h=1,None
        else:decision,h=flt.probe(int.from_bytes(raw,'little'))
        if decision==2:hit+=1;continue
        if decision==0:continue
        calls+=1;accepted[j]=1
        row=cur.execute('SELECT v FROM kv WHERE k=?',(raw,)).fetchone()
        if row is None:
            fp+=1
            if flt is not None:flt.absent(h)
        else:assert len(row[0])==32;members+=1;found[j]=1
    ns=time.perf_counter_ns()-t
    return dict(elapsed_ns=ns,ns_per_query=ns/len(seq),backend_calls=calls,fp=fp,members_found=members,cache_hits=hit)


def measure(cs,s,scores,hashes,keys,tail,seed,cur,n=20000,reps=3):
    start=time.perf_counter();flts={'NoFilter':None};preps={};out=[]
    for name in SQL_METHODS[1:]:
        t=time.perf_counter();flt=Executable(cs[name],s,scores,seed);rebuild=time.perf_counter()-t
        t=time.perf_counter();got=verify_static(s.ids,seed,flt.impl,flt.args)
        assert got[s.y].all() and np.array_equal(got[s.split['neg_test']],cs[name]['structure'].fp_static)
        # Warm feedback JIT on an actual nonmember, discard before evaluation.
        flt.absent(s.h1q[0]);flt.reset();flts[name]=flt
        preps[name]=dict(executable_rebuild_s=rebuild,query_JIT_and_static_check_s=time.perf_counter()-t,deployed_array_bytes=flt.physical_array_bytes)
    for p in PROPORTIONS:
        seq=mixed(s,tail,seed,p,n);refs={}
        for name,flt in flts.items():
            flags=np.ones(len(s.ids),np.bool_)
            if flt is not None:flags[s.split['neg_test']]=cs[name]['structure'].fp_static;spec=flt.spec
            else:spec=F.layout(0)
            data=F.allocate(spec) if spec['buckets'] else EMPTY
            accepted,found=reference(seq,hashes,s.y,flags,data,spec['buckets'],spec['Q'],spec['ob'],spec['slot_bits'],spec['handbits']);refs[name]=(accepted,found,data)
        for rep in range(reps):
            order=SQL_METHODS[rep%4:]+SQL_METHODS[:rep%4]
            for position,name in enumerate(order):
                flt=flts[name]
                if flt:flt.reset()
                accepted=np.zeros(len(seq),np.uint8);found=np.zeros_like(accepted)
                result=online(cur,keys,seq,flt,accepted,found);rm,rf,rd=refs[name]
                assert np.array_equal(accepted,rm) and np.array_equal(found,rf)
                assert result['members_found']==int(s.y[seq].sum()) and result['backend_calls']==int(accepted.sum())
                if flt:
                    assert np.array_equal(flt.data,rd);q=flt.spec;before=W.ah(flt.data)
                    assert F.count_member_hits(flt.data,s.h1m,q['buckets'],64,q['Q'],q['ob'],q['slot_bits'],4)==0 and before==W.ah(flt.data)
                out.append(dict(method=name,member_target=p,queries=n,actual_members=int(s.y[seq].sum()),negative_queries=int((~s.y[seq]).sum()),rep=rep,position=position,**result,member_fn=0,accepted_sha256=W.ah(accepted),found_sha256=W.ah(found),cache_sha256=W.ah(flt.data) if flt else None,request_sha256=W.ah(seq),reference_equal=True))
    return out,dict(executables=preps,total_measure_and_verification_s=time.perf_counter()-start)

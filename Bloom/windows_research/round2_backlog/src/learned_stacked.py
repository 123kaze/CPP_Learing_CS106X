"""Learning-prefix tuning of a physical PLBF -> negative BF -> positive BF."""
import numpy as np,time
import engine as E
BASES={}

def bf_build(hashes,nbytes,k):
    m=np.array([int(nbytes)*8],np.int64);ks=np.array([k],np.int64);off=np.array([0,int(nbytes)*8],np.int64)
    bits=np.zeros(int(nbytes),np.uint8)
    E.R.packed_build(hashes,np.zeros(len(hashes),np.int32),off,m,ks,bits)
    return bits
def bf_query(hashes,bits,k):
    return E.R.packed_query(hashes,np.zeros(len(hashes),np.int32),np.array([E.C.BF],np.uint8),
                            np.array([0,len(bits)*8],np.int64),np.array([len(bits)*8],np.int64),np.array([k],np.int64),bits)

def layers(setup,base,known,side_bytes,b2,query_indices=None):
    # Two physical BF arrays plus a64-byte descriptor. Unused Bloom reservation
    # is retained as actual BF bits, not hidden metadata or logical bit arrays.
    overhead=2*E.F.ARRAY_HEADER+64
    n2=max(1,(int(b2*len(known))+7)//8)
    n3=int(side_bytes)-overhead-n2
    if len(known)==0 or n3<1:return None
    k2=max(1,round(b2*np.log(2)))
    negative=bf_build(setup.h1q[known],n2,k2)
    member_hit=bf_query(setup.h1m,negative,k2)
    count=int(member_hit.sum())
    k3=max(1,min(32,round(n3*8/max(1,count)*np.log(2))))
    positive=bf_build(setup.h1m[member_hit],n3,k3)
    assert bf_query(setup.h1m[member_hit],positive,k3).all()
    indices=np.arange(len(setup.h1q)) if query_indices is None else query_indices
    hashes=setup.h1q[indices]
    n_hit=bf_query(hashes,negative,k2)
    p_hit=bf_query(hashes,positive,k3) if count else np.zeros(len(indices),np.bool_)
    accepted=base.fp_static[indices]&(~n_hit|p_hit)
    return dict(fp=accepted,side_bytes=n2+n3+overhead,negative_bytes=n2,positive_bytes=n3,
                negative_k=k2,positive_k=k3,members_in_positive=count,known_negatives=len(known))

def choose(setup,scores,kib,gama_t,learn,fracs=(.02,.05,.1,.2,.4,.6),b2s=(.5,1,2,4,6,8,12)):
    start=time.perf_counter();split=len(learn)//2
    counts=np.bincount(learn[split:],minlength=len(setup.h1q))
    observed=np.flatnonzero(counts)
    fallback=E.R.structure(setup,scores,gama_t,kib*1024,0,sketch_bytes=0)
    fallback_fp=int(counts[observed][fallback.fp_static[observed]].sum())
    best=((fallback_fp,fallback.est_fpr,0.,0.),0.,0.)
    records=[dict(frac=0.,b2=0.,validation_fp=fallback_fp,known=0)]
    bases={0.:fallback}
    for f in fracs:
        side=int(kib*1024*f)
        key=(id(setup),kib,gama_t,f)
        if key not in BASES:BASES[key]=E.R.structure(setup,scores,gama_t,kib*1024,side,sketch_bytes=0)
        base=BASES[key]
        if base is None:continue
        bases[f]=base
        known=np.unique(learn[:split][base.fp_static[learn[:split]]])
        for b2 in b2s:
            result=layers(setup,base,known,side,b2,observed)
            if result is None:continue
            fp=int(counts[observed][result['fp']].sum())
            record=dict(frac=f,b2=b2,validation_fp=fp,known=len(known))
            records.append(record)
            key=(fp,base.est_fpr,f,b2)
            if best is None or key<best[0]:best=(key,f,b2)
    if best is None:return None
    _,f,b2=best;base=bases[f]
    if f==0:
        return dict(base=base,frac=0.,b2=0.,selected_trees=gama_t,fp_static=base.fp_static,
                    state_bytes=base.used_bytes,learning_seconds=time.perf_counter()-start,
                    layers=dict(side_bytes=0,negative_bytes=0,positive_bytes=0,known_negatives=0),grid=records)
    known=np.unique(learn[base.fp_static[learn]])
    result=layers(setup,base,known,int(kib*1024*f),b2)
    if result is None:return None
    return dict(base=base,frac=f,b2=b2,selected_trees=gama_t,fp_static=result.pop('fp'),
                state_bytes=base.used_bytes-int(kib*1024*f)+result['side_bytes'],
                learning_seconds=time.perf_counter()-start,layers=result,grid=records)

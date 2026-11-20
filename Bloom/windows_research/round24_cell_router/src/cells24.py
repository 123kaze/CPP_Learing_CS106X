"""Static two-feature quantization / ratio-ordered region table; no cache claims."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import sys
import numpy as np
from numba import njit
WR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WR/'round12_nomodel/src'))
import baseline as BF
E5=BF.E5;D=E5.D;C=E5.C;R=E5.R;K=E5.K
FEATURES={'url':('len','digits'),'caida_tcp_flow':('src','dst')}


def cell_ids(X,feature,edges,bins):
    first=np.searchsorted(edges[0],X[:,feature[0]],side='right')
    second=np.searchsorted(edges[1],X[:,feature[1]],side='right')
    return first*bins+second


def fit_build(X,y,split,hashes,feature,bins,kib):
    if len(feature)!=2 or bins not in (16,32):raise ValueError('Fixed two-feature grid with16 or32 bins only')
    train=split['member_train']|split['neg_train']
    edge=np.quantile(X[train][:,feature],np.arange(1,bins)/bins,axis=0).T.copy()
    cell=cell_ids(X,feature,edge,bins);ncell=bins*bins
    members=np.bincount(cell[y],minlength=ncell)
    negatives=np.bincount(cell[split['neg_val']],minlength=ncell)
    # Add-one is an explicit fixed regularizer; not infinite empirical ratios or a tuned EB scheme.
    p=(members+1)/(members.sum()+ncell);q=(negatives+1)/(negatives.sum()+ncell)
    ratio=p/q;order=np.argsort(ratio,kind='stable')
    header=np.array([2401,bins,feature[0],feature[1],ncell,D.K_REG],np.int32)
    route=np.zeros((3*ncell+63)//64,np.uint64)
    feature_edges=edge.ravel().copy()
    blank=[np.empty(5,np.uint8),np.empty(6,np.int64),np.empty(5,np.int64),np.empty(5,np.int64),np.empty(0,np.uint8)]
    fixed=sum(sys.getsizeof(a) for a in [header,feature_edges,route,*blank])
    avail=(kib*1024-fixed)*8
    if avail<=0:raise ValueError('Table/metadata leaves no BF budget')
    allocation=float(avail)
    td=BF.SimpleNamespace(g=members[order])
    for _ in range(20):
        bounds,f,_=D.allocate(members[order],negatives[order]+1.,allocation)
        region=D.region_of_segment(bounds,N=ncell)
        n=np.bincount(region,weights=members[order],minlength=len(f))
        bpm=np.where((f>0)&(f<1),np.log(1/np.clip(f,1e-300,1))/(np.log(2)**2),0.)
        m=np.where(n>0,np.floor(bpm*n),0).astype(np.int64)
        kind=np.where(n==0,C.EMPTY,np.where(m>0,C.BF,C.PASS)).astype(np.uint8)
        if m.sum()<=avail:break
        allocation*=avail/m.sum()*.9999
    assert m.sum()<=avail
    cell_region=np.empty(ncell,np.int64);cell_region[order]=region
    for i,v in enumerate(cell_region):K.put(route,i*3,3,np.uint64(v))
    k=np.where(kind==C.BF,np.maximum(1,np.rint(bpm*np.log(2))),0).astype(np.int64)
    off=np.concatenate([[0],np.cumsum(m)]).astype(np.int64)
    bits=np.zeros((int(off[-1])+7)//8,np.uint8)
    key_region=cell_region[cell].astype(np.int32)
    R.packed_build(hashes[y],key_region[y],off,m,k,bits)
    flags=R.packed_query(hashes,key_region,kind,off,m,k,bits)
    assert flags[y].all()
    arrays=dict(header=header,edges=feature_edges,route=route,kind=kind,off=off,m=m,k=k,bits=bits)
    used=sum(sys.getsizeof(a) for a in arrays.values());assert used<=kib*1024
    assert all(a.flags.owndata for a in arrays.values())
    # Both raw and regularized region KL are diagnostic, not untruncated deployment guarantees.
    region_members=np.bincount(cell_region,weights=members,minlength=5)
    region_neg=np.bincount(cell_region,weights=negatives,minlength=5)
    pp=np.bincount(cell_region,weights=p,minlength=5);qq=np.bincount(cell_region,weights=q,minlength=5)
    active=pp>0
    kl=float(np.sum(pp[active]*np.log(pp[active]/qq[active])))
    report=dict(total_bytes=used,cell_count=ncell,packed_table_payload_bytes=route.nbytes,
                router_bytes=sum(sys.getsizeof(a) for a in (header,feature_edges,route)),
                bin_edges_payload_bytes=feature_edges.nbytes,filter_payload_bytes=bits.nbytes,
                metadata_and_headers_bytes=used-bits.nbytes-route.nbytes-feature_edges.nbytes,
                nonempty_member_cells=int(np.count_nonzero(members)),nonempty_validation_cells=int(np.count_nonzero(negatives)),
                zero_validation_member_cells=int(((members>0)&(negatives==0)).sum()),
                region_members=region_members.astype(int).tolist(),region_validation_negatives=region_neg.astype(int).tolist(),
                smoothed_region_KL=kl,regions=len(f),regularizer='add-one to both cell count histograms',
                note='Static T=0 diagnostic. Ratio order and DP are based on smoothed estimated distributions; no global arbitrary-feature partition guarantee.')
    return arrays,flags,report


@njit(cache=True)
def lookup_region(row,header,edges,route):
    bins=np.int64(header[1]);a=np.int64(header[2]);b=np.int64(header[3])
    i=np.searchsorted(edges[:bins-1],row[a],side='right')
    j=np.searchsorted(edges[bins-1:],row[b],side='right')
    return np.int64(K.get(route,(i*bins+j)*3,3))


@njit(cache=True)
def query(X,hashes,idx,header,edges,route,kind,off,m,k,bits):
    out=np.empty(len(idx),np.bool_)
    for q,x in enumerate(idx):
        r=lookup_region(X[x],header,edges,route)
        yes=kind[r]==C.PASS
        if kind[r]==C.BF:
            yes=True
            for j in range(k[r]):
                p=off[r]+C.bf_pos(hashes[x],j,m[r])
                if (bits[p>>3]>>np.uint8(p&7))&np.uint8(1)==0:yes=False;break
        out[q]=yes
    return out


@njit(cache=True)
def router_checksum(X,idx,header,edges,route):
    total=0
    for i in idx:total+=lookup_region(X[i],header,edges,route)
    return total

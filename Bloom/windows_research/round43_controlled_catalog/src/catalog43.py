"""Controlled catalogue and unchanged-selector adapters; raw key domain is exactly uint64."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round27_http_real/src'))
import worker27 as W
sys.path.insert(0,str(WR/'round10_fpcache/src'))
import cache_fp as F
sys.path.insert(0,str(WR/'round37_clarknet_controls/src'))
import control37 as CTRL
from contextlib import contextmanager
from types import SimpleNamespace
import numpy as np
import json,time,hashlib
E5=W.E5;RA=W.ra5;R6=W.ra6;B=W.B;K_ORIGINAL=E5.K
SEEDS=(4301,4302,4303);STRENGTHS=(0,6);ASSOCIATIONS=('neutral','high_hot','low_hot');BUDGETS=(16,32,64)
METHODS=('Gama','Replay','RA-global','RA6','BF+Cache','PlainBF','ZGate')


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in f.get(group,{}).items():assert W.sha(BLOOM/p)==h,p
    return W.sha(ROOT/'plan/freeze.json')


@contextmanager
def exact64():
    assert E5.K is K_ORIGINAL
    E5.K=F
    try:yield
    finally:E5.K=K_ORIGINAL


def catalogue(strength,seed,nm=65536,ndev=16384,nq=65536):
    rng=np.random.default_rng(seed);bins=np.arange(256);z=bins/255-.5
    pm=np.exp(strength*z);pm/=pm.sum();pn=np.exp(-strength*z);pn/=pn.sum()
    nneg=2*ndev+nq
    feature=np.concatenate([rng.choice(256,nm,p=pm),rng.choice(256,nneg,p=pn)]).astype(np.uint64)
    suffix=rng.integers(0,1<<56,len(feature),dtype=np.uint64)
    ids=(feature<<np.uint64(56))|suffix;assert len(np.unique(ids))==len(ids),'Raw key duplicate; refuse regeneration'
    y=np.arange(len(ids))<nm;X=(feature.astype(np.float32)/np.float32(255)).reshape(-1,1).copy()
    mt=np.zeros(len(ids),np.bool_);mt[:nm]=rng.random(nm)<.5
    nt=np.zeros_like(mt);nt[nm:nm+ndev]=True
    nv=np.zeros_like(mt);nv[nm+ndev:nm+2*ndev]=True
    nqmask=~(y|nt|nv);sp=dict(member_train=mt,neg_train=nt,neg_val=nv,neg_test=nqmask)
    h=E5.C.splitmix64(ids^np.uint64(E5.C.H1_SALT)^np.uint64(seed))
    s=SimpleNamespace(name=f'controlled_a{strength}_s{seed}',ids=ids,y=y,split=sp,h1m=h[y],h1q=h[nqmask],q_ids=ids[nqmask])
    assert len(np.unique(h))==len(h),'Bijective uint64 hash contract broken'
    mb=np.bincount(feature[y].astype(np.int64),minlength=256);qb=np.bincount(feature[nqmask].astype(np.int64),minlength=256)
    return s,X,h,dict(strength=strength,seed=seed,members=nm,train_negative_keys=ndev,validation_negative_keys=ndev,query_negative_keys=nq,member_feature_bins=int((mb>0).sum()),negative_feature_bins=int((qb>0).sum()),query_keys_sharing_member_feature=int(qb[mb>0].sum()),feature_support_rule_negative_key_rejects=int(qb[mb==0].sum()),raw_ids_sha256=W.ah(ids),features_sha256=W.ah(X),member_hashes_sha256=W.ah(s.h1m),query_hashes_sha256=W.ah(s.h1q))


def probabilities(s,association,seed):
    feature=(s.q_ids>>np.uint64(56)).astype(np.int64);region=np.minimum(4,feature*5//256)
    ordered=np.array([.4,.7,1.,1.3,1.6])
    powers=np.ones(5) if association=='neutral' else ordered if association=='high_hot' else ordered[::-1].copy()
    assert association in ASSOCIATIONS
    rng=np.random.default_rng(seed+43000);prob=np.zeros(len(feature));mass=np.bincount(region,minlength=5)/len(region)
    for g in range(5):
        ix=np.flatnonzero(region==g);rng.shuffle(ix)
        if not len(ix):continue
        w=np.arange(1,len(ix)+1,dtype=float)**(-powers[g]);prob[ix]=mass[g]*w/w.sum()
    assert np.isclose(prob.sum(),1.) and np.allclose(np.bincount(region,weights=prob,minlength=5),mass)
    return prob,region,powers,mass


def stream(s,association,seed,n=1000000):
    prob,region,powers,mass=probabilities(s,association,seed);cdf=np.cumsum(prob);cdf[-1]=1.
    draws=np.random.default_rng(seed+86000).random(n);seq=np.searchsorted(cdf,draws).astype(np.int64);cut=n//4
    counts=np.bincount(seq[:cut],minlength=len(s.h1q));diagnostics=[]
    for g in range(5):
        c=counts[region==g];L=int(c.sum());diagnostics.append(dict(region=g,exponent=float(powers[g]),query_mass=float(mass[g]),learning_queries=L,learning_distinct=int((c>0).sum()),learning_repeat_fraction=1-float((c>0).sum())/L if L else None))
    return seq[:cut],seq[cut:],dict(stream_sha256=W.ah(seq),learning_sha256=W.ah(seq[:cut]),tail_sha256=W.ah(seq[cut:]),probabilities_sha256=W.ah(prob),regions=diagnostics)


def train(s,X,seed):
    t=time.perf_counter();sp=s.split;use=sp['member_train']|sp['neg_train']
    model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[use],label=s.y[use]),num_boost_round=200)
    train_s=time.perf_counter()-t;assert model.num_trees()==200
    t=time.perf_counter();scores=W.prefix_raw_scores(model,X,E5.TREES)
    for trees in E5.TREES:E5.R._MODEL_ARRAYS[s.name,trees]=W.model_arrays(model,trees)
    score_s=time.perf_counter()-t
    t=time.perf_counter()
    for trees in E5.TREES:E5.tree(s,scores,trees)
    tree_s=time.perf_counter()-t
    held=(s.y&~sp['member_train'])|sp['neg_val']
    auc={str(t):W.auc(s.y[held],scores[t][held]) for t in E5.TREES}
    s.q_score=scores[200][sp['neg_test']]
    return scores,dict(training_s=train_s,score_s=score_s,shared_tree_s=tree_s,development_auc_by_trees=auc,model_sha256=hashlib.sha256(model.model_to_string().encode()).hexdigest())


def evaluate(c,seq,s):
    spec=F.layout(c['cache_bytes']);data=F.allocate(spec);t=time.perf_counter()
    cnt=F.replay(seq,s.h1q,np.empty(0,np.bool_),c['structure'].fp_static,data,spec['buckets'],64,spec['Q'],spec['ob'],spec['slot_bits'],4,spec['handbits'],2**62,np.empty(0,np.int64),np.empty(0,np.bool_))
    replay_s=time.perf_counter()-t;assert cnt[5]==len(seq) and cnt[6]==cnt[8]==0
    t=time.perf_counter();hits=F.count_member_hits(data,s.h1m,spec['buckets'],64,spec['Q'],spec['ob'],spec['slot_bits'],4);assert hits==0
    return dict(fp=int(cnt[0]),cache_hits=int(cnt[1]),evictions=int(cnt[3]),occupied=int(cnt[7]),member_fn=0,replay_s=replay_s,all_member_check_s=time.perf_counter()-t,cache_sha256=W.ah(data)),data


def select_all(s,scores,learn,lm,kib,H):
    assert E5.K is F
    t=time.perf_counter();g=E5.gama(E5.candidates(s,scores,kib,fracs=(0.,)));gs=time.perf_counter()-t
    t=time.perf_counter();candidates=E5.candidates(s,scores,kib);grid=time.perf_counter()-t
    t=time.perf_counter();rep,_=E5.replay_best(candidates,learn,s,None);replay=time.perf_counter()-t
    t=time.perf_counter();glob,gi=RA.select(s,scores,lm,kib,H,RA.Config(mode='global',new_mix=0.));glob_s=time.perf_counter()-t
    t=time.perf_counter();ra,ri=R6.select6(s,scores,lm,kib,H);ra_s=time.perf_counter()-t
    bfs=[];btimes=[]
    for f in E5.FRACS:
        t=time.perf_counter();bfs.append(B.build(s,kib,f,F));btimes.append(time.perf_counter()-t)
    t=time.perf_counter();bf,_=E5.replay_best(bfs,learn,s,None);br=time.perf_counter()-t;bf_s=sum(btimes)+br
    t=time.perf_counter();rf=E5.evaluate(ra,learn,s,None)['fp'];bf_l=E5.evaluate(bf,learn,s,None)['fp'];gate=bf if bf_l<=rf else ra;gate_s=time.perf_counter()-t
    cs=dict(zip(METHODS,(g,rep,glob,ra,bf,bfs[0],gate)))
    times=dict(zip(METHODS,(gs,grid+replay,glob_s,ra_s,bf_s,btimes[0],ra_s+bf_s+gate_s)))
    return cs,times,dict(RA6=ri,RA_global=gi,replay_candidates=len(candidates),replay_grid_s=grid,replay_learning_s=replay,zgate_winner='BF+Cache' if gate is bf else 'RA6',ra_learning_fp=rf,bf_learning_fp=bf_l)


def ledger(c):
    st=c['structure'];parts=dict(model_bytes=int(st.model_bytes),bf_bytes=int(st.filter_bytes),routing_bytes=int(st.metadata_bytes),headers=int(st.array_overhead_bytes),cache_bytes=int(c['cache_bytes']))
    assert sum(parts.values())==st.used_bytes<=st.budget_bytes
    return dict(**parts,total_bytes=int(st.used_bytes),required_backend_index_bytes=0,cache_slots=int(c['slots']),trees=c['trees'],cache_frac=c['frac'])


def controls(s,scores,lm,H,kib,tail):
    M=CTRL.M;start=time.perf_counter();anchors=E5.candidates(s,scores,kib,fracs=(.1,))
    if not anchors:return dict(status='infeasible',rows=[])
    c=min(anchors,key=lambda c:(c['structure'].est_fpr,c['trees']));st=c['structure'];td=E5.tree(s,scores,c['trees']);reg=E5.D.region_of_segment(st.b)
    mr=reg[td.seg_m].astype(np.int32);qr=reg[td.seg_q].astype(np.int32);n=np.bincount(mr,minlength=5).astype(float);h=np.bincount(reg,weights=td.h,minlength=5)
    bits=int((kib*1024-td.fixed-c['cache_bytes'])*8);eh=M.capped(n,h,bits);P=RA.population(lm,td,H,RA.Config(new_mix=0.));mass=CTRL.region_masses(P,td,reg,eh,c['slots']);identity=M.identity(n,h,mass['miss'],bits)
    shared_s=time.perf_counter()-start;rows=[]
    for arm in ('h','traffic','miss'):
        t=time.perf_counter();eps=M.capped(n,mass[arm],bits);flags,meta=M.physical(n,eps,s.h1m,s.h1q,mr,qr,bits);build_s=time.perf_counter()-t
        toy=dict(c);toy['structure']=SimpleNamespace(fp_static=flags)
        res,_=evaluate(toy,tail,s);used=int(td.fixed+c['cache_bytes']+meta['payload_bytes']);assert used<=kib*1024
        rows.append(dict(arm=arm,**res,total_bytes=used,weights=mass[arm].tolist(),physical=meta,build_s=build_s,flags_sha256=W.ah(flags)))
    return dict(status='complete',trees=c['trees'],partition=st.b.tolist(),cache_bytes=c['cache_bytes'],bf_bits=bits,shared_prepare_s=shared_s,conditional_identity=identity,actual_clock_fixed_T=False,rows=rows)

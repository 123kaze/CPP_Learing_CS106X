"""Explicit rate/missing-mass ablations; original count semantics and files stay intact."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
for r in ('round5_dp','round6_bucket','round10_fpcache','round19_gt_fix'):sys.path.insert(0,str(WR/r/'src'))
import ra6
import ra5 as RA
import cache_fp
from summarize19 import summarize19
import numpy as np
from types import SimpleNamespace
from contextlib import contextmanager
import time,json,hashlib
E5=ra6.E5
CACHES={'index':E5.K,'fp64':cache_fp}
ARMS=('GT19','SeenNormalize','TotalNormalize')
ORIGINAL_POPULATION=RA.population
ORIGINAL_BUCKET=ra6.bucket_prediction
ORIGINAL_TABLE=RA.candidate_table


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.json.tmp');q.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');q.replace(p)


def normalize(lm,arm):
    if arm not in ARMS or lm.L<=0:raise ValueError('Unknown arm or empty learning input')
    rate=np.asarray(lm.rate,np.float64);R=float(rate.sum());u=lm.N1/lm.L;Z=R+u
    assert np.isfinite(rate).all() and (rate>=0).all() and 0<=u<=1 and Z>0
    if arm=='GT19':factor=1.;new=rate.copy();unseen=u
    elif arm=='SeenNormalize':
        if R==0:
            if u!=1:raise ValueError('Zero seen mass with unexplained missing probability')
            factor=1.;new=rate.copy()
        else:factor=(1-u)/R;new=rate*factor
        unseen=u
    else:factor=1/Z;new=rate*factor;unseen=u/Z
    changed=not (np.array_equal(new.view(np.uint8),rate.view(np.uint8)) and unseen==u)
    out=SimpleNamespace(**{**vars(lm),'rate':new,'unseen_mass':unseen,'normalization_arm':arm,'normalization_changed':changed})
    assert out.L==lm.L and out.N1==lm.N1 and out.counts is lm.counts
    total=float(new.sum()+unseen)
    if arm!='GT19':assert abs(total-1)<1e-12 and new.max(initial=0)<=1+1e-12
    return out,dict(arm=arm,raw_seen_mass=R,raw_unseen_mass=u,raw_total_mass=Z,seen_mass=float(new.sum()),unseen_mass=unseen,total_mass=total,
                    rate_scale=factor,raw_rate_sha256=ah(rate),new_rate_sha256=ah(new),changed=changed,L=lm.L,N1=lm.N1)


def normalized_population(lm,td,H,cfg):
    if not lm.normalization_changed:return ORIGINAL_POPULATION(lm,td,H,cfg)
    k=E5.D.N_SEG;seg=td.seg_q[lm.keys];urate,ridx=np.unique(lm.rate,return_inverse=True)
    w=np.bincount(seg*len(urate)+ridx,minlength=k*len(urate)).astype(np.float64);nz=np.flatnonzero(w)
    f1=np.bincount(seg[lm.counts==1],minlength=k)
    G=H*lm.unseen_mass*(cfg.new_mix*f1/max(lm.N1,1)+(1-cfg.new_mix)*td.h)
    return RA.ra4.Population(nz//len(urate),urate[nz%len(urate)],w[nz],G,td.g.astype(float),td.h,H)


def normalized_bucket(setup,lm,td,c,H,seg_fpr):
    if not lm.normalization_changed:return ORIGINAL_BUCKET(setup,lm,td,c,H,seg_fpr)
    fpk=c['structure'].fp_static[lm.keys];lam=lm.rate[fpk]
    G=H*lm.unseen_mass*td.h;new=float((seg_fpr*G).sum())
    if c['cache_bytes']==0:return float((lam*H).sum())+new
    nb=c['slots']//ra6.WAYS;b=ra6.buckets_of(setup.h1q[lm.keys[fpk]],nb)
    return ra6.bucket_che(lam,b,nb,H,new/H/nb)+new


@contextmanager
def adapted(arm):
    assert RA.population is ORIGINAL_POPULATION and ra6.bucket_prediction is ORIGINAL_BUCKET and RA.candidate_table is ORIGINAL_TABLE,'Nested/leaked adaptation'
    capture={}
    def table(*args,**kwargs):
        result=ORIGINAL_TABLE(*args,**kwargs);capture['table']=result;return result
    RA.candidate_table=table
    if arm!='GT19':RA.population=normalized_population;ra6.bucket_prediction=normalized_bucket
    try:yield capture
    finally:
        RA.population=ORIGINAL_POPULATION;ra6.bucket_prediction=ORIGINAL_BUCKET;RA.candidate_table=ORIGINAL_TABLE


def select(setup,scores,lm,kib,H,arm):
    normalize_start=time.perf_counter()
    transformed,diagnostic=normalize(lm,arm)
    normalization_s=time.perf_counter()-normalize_start
    start=time.perf_counter()
    with adapted(arm) as capture:
        chosen,info=ra6.select6(setup,scores,transformed,kib,H)
    select_s=time.perf_counter()-start
    timer=time.perf_counter()
    ordered=sorted(capture['table'],key=lambda r:(r['pred'],r['trees'],r['frac']))
    table=[dict(rank=i,trees=r['trees'],frac=r['frac'],cache_bytes=r['cache_bytes'],slots=r['slots'],predicted_fp=float(r['pred']),weights_sha256=ah(r['weights']),fpr_sha256=ah(r['seg_fpr_pred'])) for i,r in enumerate(ordered)]
    return chosen,dict(info,selector_wall_s=select_s,normalization_s=normalization_s,normalize_and_select_s=normalization_s+select_s,rank_serialization_s=time.perf_counter()-timer,normalization=diagnostic,table=table)

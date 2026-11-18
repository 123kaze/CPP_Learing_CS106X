"""RA6-Z: add physically accounted zero-tree candidates to the predictive shortlist.

This is a NEW method, not a change to frozen RA6. Same global top-five rule and
bucket refinement; no learning-trace replay or evaluation outcomes select RA6-Z.
"""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[v]='1'
import sys
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
WR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WR/'round6_bucket/src'))
import ra6
sys.path.insert(0,str(WR/'round12_nomodel/src'))
import baseline as BF
E5,RA=ra6.E5,ra6.RA


def zero_table(setup,lm,kib,H,fracs=E5.FRACS):
    """One score segment; exact physical BF capacity and integer-k ideal FPR.

    No model, learned segmentation, DP metadata or model-array headers are charged.
    The same Good–Turing/Che/set-associative predictor is reused, not tuned on TCP.
    """
    if lm.L<=0 or H<=0 or len(setup.h1m)==0:raise ValueError('Nonempty members/learning and positive horizon required')
    rates,multiplicity=np.unique(lm.rate,return_counts=True)
    P=RA.ra4.Population(np.zeros(len(rates),np.int64),rates,multiplicity.astype(np.float64),
                        np.array([H*lm.N1/lm.L]),np.array([len(setup.h1m)],np.float64),np.ones(1),H)
    rows=[]
    for frac in fracs:
        cb,slots=E5.cache_alloc(kib*1024,frac)
        try:data=BF.allocate(len(setup.h1m),kib*1024,cb)
        except ValueError:continue
        m,k=int(data[1]),int(data[2])
        e=(-np.expm1(-k*len(setup.h1m)/m))**k
        fpr=np.array([e]);pred=float(fpr@P.misses(fpr,slots,True))
        rows.append(dict(trees=0,frac=float(frac),cache_bytes=cb,slots=slots,weights=None,
                         pred=pred,seg_fpr_pred=fpr,bf_bits=m,bf_k=k,family='zero'))
    return rows


def build_row(setup,scores,kib,row):
    if row['trees']==0:
        c=BF.build(setup,kib,row['frac'],E5.K)
        assert c['cache_bytes']==row['cache_bytes'] and c['slots']==row['slots']
        assert int(c['structure'].data[1])==row['bf_bits'] and int(c['structure'].data[2])==row['bf_k']
        return c
    return E5.build(setup,scores,row['trees'],kib,row['frac'],weights=row['weights'],
                    cache_bytes=row['cache_bytes'],slots=row['slots'])


def select(setup,scores,lm,kib,H,topk=5,trees=E5.TREES,fracs=E5.FRACS,include_zero=True):
    if topk<1:raise ValueError('topk must be positive')
    start=time.perf_counter()
    # Do not call the learned path at all if caller explicitly supplies no learned prefixes.
    learned=RA.candidate_table(setup,scores,lm,kib,H,RA.Config(new_mix=0.),trees=trees,fracs=fracs) if trees else []
    table=learned+(zero_table(setup,lm,kib,H,fracs) if include_zero else [])
    if not table:raise ValueError('No feasible candidates')
    table_done=time.perf_counter()
    ranked=sorted(table,key=lambda r:(r['pred'],r['trees'],r['frac']))
    best=None;audit=[]
    for rank,row in enumerate(ranked[:topk]):
        c=build_row(setup,scores,kib,row)
        td=SimpleNamespace(h=np.ones(1)) if row['trees']==0 else E5.tree(setup,scores,row['trees'])
        pred=ra6.bucket_prediction(setup,lm,td,c,H,row['seg_fpr_pred'])
        audit.append(dict(rank=rank,trees=row['trees'],frac=row['frac'],stage1_pred=float(row['pred']),refined_pred=pred,
                          cache_bytes=c['cache_bytes'],used_bytes=c['structure'].used_bytes))
        if best is None or (pred,rank)<best[0]:best=((pred,rank),c)
    end=time.perf_counter();(pred,rank),c=best
    info=dict(method='RA6-Z',trees=c['trees'],frac=c['frac'],predicted_fp=pred,rank=rank,
              candidates=len(table),learned_candidates=len(learned),zero_candidates=len(table)-len(learned),
              built=len(audit),stage1_s=table_done-start,build_refine_s=end-table_done,select_s=end-start,
              shortlist=audit,zero_min_stage1_rank=next((i for i,r in enumerate(ranked) if r['trees']==0),None))
    return c,info

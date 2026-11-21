"""Explicit post-hoc no-repeat variant. All repeated inputs delegate unchanged."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round6_bucket/src'))
import ra6
E5=ra6.E5
import numpy as np


def no_repeat(lm):
    if lm.L<=0:raise ValueError('Nonempty learning input required')
    return bool(len(lm.counts)==lm.L and np.all(lm.counts==1))


def select(setup,scores,lm,kib,H,topk=5):
    if no_repeat(lm):
        t=time.perf_counter();candidates=E5.candidates(setup,scores,kib,fracs=(0.,))
        chosen=E5.gama(candidates)
        return chosen,dict(variant='RA6-NR32',path='exact_Gama',trees=chosen['trees'],frac=chosen['frac'],
                           candidates=len(candidates),built=len(candidates),select_build_s=time.perf_counter()-t)
    t=time.perf_counter();chosen,info=ra6.select6(setup,scores,lm,kib,H,topk=topk)
    return chosen,dict(info,variant='RA6-NR32',path='unchanged_RA6',delegated_wall_s=time.perf_counter()-t)

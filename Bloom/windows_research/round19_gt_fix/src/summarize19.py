"""Minimal count-gap repair; copied statistics logic, not a normalized estimator.

Only changed branch: for gt=True and2<=c<=GT_MAX, retain empirical c when the
next frequency class is empty. Singleton, counts aboveGT_MAX and gt=False stay
exactly as in the frozen round4 function. No smoothing, floors or renormalizing.
"""
from types import SimpleNamespace
import numpy as np
GT_MAX=5


def summarize19(learn,gt=True):
    keys,counts=np.unique(learn,return_counts=True)
    L=len(learn)
    Nc=np.bincount(counts)
    adj=counts.astype(np.float64)
    for c in range(1,GT_MAX+1):
        if gt and c<len(Nc) and Nc[c]:
            nxt=Nc[c+1] if c+1<len(Nc) else 0
            if c>=2 and nxt==0:
                continue
            adj[counts==c]=min(c,(c+1)*nxt/Nc[c])
    return SimpleNamespace(keys=keys,counts=counts,rate=adj/L,L=L,
        N1=(int(Nc[1]) if len(Nc)>1 else 0) if gt else 0,
        state_bytes=keys.nbytes+counts.nbytes)

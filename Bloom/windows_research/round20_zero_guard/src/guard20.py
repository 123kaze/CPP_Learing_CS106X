"""RA6-ZGate: protect the ordinary BF family with exact learning-window replay.

The guarantee is empirical learning FP only. No evaluation-tail observations or
labels are inputs to this selector. H is a query-count horizon, not tail data.
"""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[v]='1'
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round17_zerotree/src'))
import zero17 as Z
from native_zero17 import ZeroTreeFilter,verify_negative_stream
sys.path.insert(0,str(WR/'round19_gt_fix/src'))
from entry19 import patched,ORIGINAL_SUMMARIZE
E5=Z.E5;BF=Z.BF


def gate_family(bf_fp,learned_fp):
    """Deterministic tie rule: deploy no model when measured learning FP ties."""
    if bf_fp<0 or learned_fp<0:raise ValueError('FP counts must be nonnegative')
    return 'zero' if bf_fp<=learned_fp else 'learned'


def replay_bf_family(candidates,learn,setup,safe):
    if not candidates or any(c['trees']!=0 for c in candidates):raise ValueError('Require zero-tree candidates')
    start=time.perf_counter();freq=np.bincount(learn,minlength=len(setup.h1q))
    best=None;records=[]
    for c in sorted(candidates,key=lambda x:x['structure'].est_fpr):
        st=c['structure'];limit=best[0] if best else 2**62
        if c['cache_bytes']==0:fp,cut,processed=int(freq[st.fp_static].sum()),False,0
        else:
            r=E5.K.simulate(learn,setup.h1q,safe,st.fp_static,c['cache_bytes'],E5.PREFIX,E5.WAYS,limit=limit)
            fp,cut,processed=r['fp'],bool(r['cutoff']),r['processed']
        records.append(dict(frac=c['frac'],fp=fp,cutoff=cut,processed=processed,cache_bytes=c['cache_bytes']))
        key=(fp,st.est_fpr,c['trees'],c['frac'])
        if not cut and (best is None or key<best):best=key;winner=c
    return winner,best[0],records,time.perf_counter()-start


def select(setup,scores,safe,learn,kib,H):
    if not len(learn) or H<=0:raise ValueError('Nonempty learning stream and positive horizon required')
    # Hash checks belong to provenance, not algorithm runtime.
    with patched():
        start=time.perf_counter()
        lm=Z.RA.ra4.summarize(learn,True);summary_end=time.perf_counter()
        anchor,info=Z.ra6.select6(setup,scores,lm,kib,H);anchor_end=time.perf_counter()
        zeros=[BF.build(setup,kib,f,E5.K) for f in E5.FRACS];build_end=time.perf_counter()
        baseline,bf_fp,records,bf_replay_s=replay_bf_family(zeros,learn,setup,safe)
        t=time.perf_counter()
        # Full scan of the single learned anchor: obtain its exact learning cost,
        # rather than substituting the predicted FP or comparing different objectives.
        measured=E5.evaluate(anchor,learn,setup,safe)
        anchor_fp=int(measured['fp']);anchor_replay_s=time.perf_counter()-t
        family=gate_family(bf_fp,anchor_fp)
        chosen=baseline if family=='zero' else anchor
        end=time.perf_counter()
    selected_fp=bf_fp if family=='zero' else anchor_fp
    assert selected_fp==min(bf_fp,anchor_fp)
    return chosen,anchor,baseline,dict(method='RA6-ZGate',family=family,selected_learning_fp=selected_fp,
         zero_learning_fp=bf_fp,anchor_learning_fp=anchor_fp,empirical_nonregression=True,
         summary_s=summary_end-start,anchor_select_build_s=anchor_end-summary_end,
         zero_candidates_build_s=build_end-anchor_end,zero_replay_s=bf_replay_s,
         anchor_replay_s=anchor_replay_s,selection_s=end-start,
         zero_candidates=len(zeros),learned_finalists=1,anchor_info=info,replay_records=records,
         zero_processed_queries=sum(r['processed'] for r in records),
         repaired_rate_sha256=__import__('hashlib').sha256(memoryview(lm.rate).cast('B')).hexdigest())

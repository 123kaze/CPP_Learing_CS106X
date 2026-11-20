"""Learning-only transfer of fixed-reference escape mass to disjoint training keys."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name]='1'
from pathlib import Path
import sys
import numpy as np
from scipy.special import expit
WR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WR/'round6_bucket/src'));import ra6
sys.path.insert(0,str(WR/'round19_gt_fix/src'));from summarize19 import summarize19
E5=ra6.E5;RA=ra6.RA
GROUPS=32;FLOOR=1e-6


def transfer_weights(mass,train_bins):
    """Each negative weight is estimated query-mass/training-density in its bin.

    Normalize mean negative weight to1, preserving total class-weight balance.
    Unsupported bins are disclosed; a tiny fixed floor prevents zero sample weights.
    """
    mass=np.asarray(mass,np.float64)
    freq=np.bincount(train_bins,minlength=len(mass));prior=freq/freq.sum()
    if mass.sum()<=0:raise ValueError('No finite positive proxy mass')
    target=mass/mass.sum();target=(1-FLOOR)*target+FLOOR*prior
    supported=freq>0;coverage=float(target[supported].sum())
    per=np.zeros(len(mass));per[supported]=target[supported]/prior[supported]
    weights=per[train_bins].copy();weights/=weights.mean()
    assert np.isfinite(weights).all() and np.all(weights>0) and np.isclose(weights.mean(),1)
    return weights,dict(target_mass=target.tolist(),train_counts=freq.tolist(),supported_target_mass=coverage,
                        negative_weight_min=float(weights.min()),negative_weight_max=float(weights.max()),
                        negative_weight_quantiles=np.quantile(weights,[0,.1,.5,.9,.99,1]).tolist(),
                        mean_negative_weight=float(weights.mean()))


def estimate(reference_scores,labels,split,reference_c,reference_td,learn,H):
    # Scalar rank bins derived from training negatives; no evaluation values are used.
    tr=split['neg_train'];val=split['neg_val'];members=labels
    cut=np.quantile(reference_scores[tr],np.arange(1,GROUPS)/GROUPS)
    train_bin=np.searchsorted(cut,reference_scores[tr],side='right')
    val_bin=np.searchsorted(cut,reference_scores[val],side='right')
    member_bin=np.searchsorted(cut,reference_scores[members],side='right')
    # Only learning key scores are fetched from the negative test pool, never its tail counts.
    pool_scores=reference_scores[split['neg_test']]
    lm=summarize19(learn,True)
    key_bin=np.searchsorted(cut,pool_scores[lm.keys],side='right')
    g=np.bincount(member_bin,minlength=GROUPS).astype(np.float64)
    vc=np.bincount(val_bin,minlength=GROUPS)
    h=(vc+1)/(vc.sum()+GROUPS)
    unique_rates,ri=np.unique(lm.rate,return_inverse=True)
    hist=np.bincount(key_bin*len(unique_rates)+ri,minlength=GROUPS*len(unique_rates))
    nz=np.flatnonzero(hist)
    P=RA.ra4.Population(nz//len(unique_rates),unique_rates[nz%len(unique_rates)],hist[nz].astype(np.float64),
                         H*lm.N1/lm.L*h,g,h,H)
    # Reference16-tree static regional probabilities, averaged on reserved validation negatives.
    seg=E5.D.segment_of(expit(reference_scores[val]))
    weighted=np.bincount(val_bin,weights=reference_c['structure'].seg_fpr_cont[seg],minlength=GROUPS)
    epsilon=np.ones(GROUPS)
    np.divide(weighted,vc,out=epsilon,where=vc>0)
    traffic=P.Mg[0].copy();escape=P.misses(epsilon,reference_c['slots'],True)
    assert np.all(escape<=traffic+1e-8*np.maximum(1,traffic)) and np.all(escape>=0)
    wt,mt=transfer_weights(traffic,train_bin);we,me=transfer_weights(escape,train_bin)
    return dict(Uniform=np.ones(int(tr.sum())),TrafficGT=wt,EscapeGT=we),dict(
        groups=GROUPS,cuts=cut.tolist(),reference_epsilon=epsilon.tolist(),member_counts=g.tolist(),
        validation_counts=vc.tolist(),GT_N1=lm.N1,learning_queries=lm.L,H=H,
        traffic_mass=traffic.tolist(),escape_mass=escape.tolist(),traffic_transfer=mt,escape_transfer=me,
        note='Bin-level transfer of frozen GT/Che residual proxy, not oracle per-key future escape counts; conditioned on fixed16-tree/10%-cache reference.')

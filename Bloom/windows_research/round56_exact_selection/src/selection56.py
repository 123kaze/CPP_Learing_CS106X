"""Time only the unchanged round55 selection paths; no new estimator/replay optimization."""
import sys,time
from common56 import C,np


def select(d,method,kib,learn,H):
    start=time.perf_counter();cpu=time.process_time();s,scores=d.s,d.scores
    meta=dict(summary_s=0.,grid_build_s=0.,learning_replay_s=0.,predict_build_refine_s=0.)
    aux=None
    if method in ('Gama','Replay'):
        grid=[]
        for tr in C.E5.TREES:
            for frac in ((0.,) if method=='Gama' else C.E5.FRACS):
                c=C.E5.build(s,scores,tr,kib,frac)
                if c is not None:grid.append(c)
        meta['grid_build_s']=time.perf_counter()-start
        if method=='Gama':
            chosen=C.E5.gama(grid)
        else:
            t=time.perf_counter();chosen,records=d.e.best(grid,learn)
            meta['learning_replay_s']=time.perf_counter()-t
            meta['learning_replay_records']=records
        meta.update(candidates=len(grid),built=len(grid))
        aux=grid
    elif method=='RA6':
        t=time.perf_counter();lm=C.summarize19(learn);meta['summary_s']=time.perf_counter()-t
        t=time.perf_counter();chosen,info=C.R6.select6(s,scores,lm,kib,H,C.RA.Config(new_mix=0.),topk=5)
        meta['predict_build_refine_s']=time.perf_counter()-t
        meta.update(candidates=info['candidates'],built=info['built'],prediction=info['predicted_fp'],rank=info['ra4_rank'])
        aux=lm
    else:raise ValueError(method)
    meta.update(selection_s=time.perf_counter()-start,selection_cpu_s=time.process_time()-cpu)
    # Accounting below is outside the selection timer.
    if method=='RA6':
        meta.update(distinct_keys=len(aux.keys),count_payload_bytes=aux.keys.nbytes+aux.counts.nbytes,
                    count_rate_payload_bytes=aux.keys.nbytes+aux.counts.nbytes+aux.rate.nbytes,
                    count_rate_physical_bytes=sum(sys.getsizeof(x) for x in (aux.keys,aux.counts,aux.rate)))
    if method=='Replay':
        meta['bincount_temporary_payload_bytes']=len(s.h1q)*np.dtype(np.int64).itemsize
    return chosen,meta,aux

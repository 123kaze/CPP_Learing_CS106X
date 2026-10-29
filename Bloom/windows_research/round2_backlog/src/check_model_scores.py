"""Check that cached score rows and saved LightGBM models really agree."""
import json,sys
import numpy as np
import lightgbm as lgb
import engine as E
def check(ds):
    folder=E.ROOT/'cache'/ds
    with np.load(folder/'data.npz') as a:
        n=len(a['ids']);indices=np.arange(0,n,max(1,n//5000));X=a['X'][indices]
    booster=lgb.Booster(model_file=str(folder/'model200.txt'))
    errors={}
    with np.load(folder/'gama_scores.npz') as a:
        for t in E.R.GAMA_TREES:
            predicted=booster.predict(X,raw_score=True,num_iteration=t,num_threads=1)
            error=float(np.max(np.abs(predicted-a['t'+str(t)][indices])))
            assert error<1e-10,(ds,t,error)
            errors[str(t)]=error
    out=dict(status='passed',dataset=ds,rows=n,checked_rows=len(indices),prefix_max_abs_errors=errors)
    E.save(E.ROOT/'evidence'/'score-agreement'/f'{ds}.json',out);print('SCORE AGREEMENT',ds,max(errors.values()),flush=True)
    return out
if __name__=='__main__':
    for ds in sys.argv[1:]:check(ds)

import json,numpy as np,lightgbm as lgb
import engine as E
import live_pipeline as L
setup,scores,safe=E.load('url');_,_,X,_=E.C.load_dataset('url')
mixed=L.Old.make_mixed_stream(setup,.5,10000,'zipf1.1-10k')
c=E.build(setup,scores,24,64,.1)
booster=lgb.Booster(model_file=str(E.C.CACHE/'url'/'model200.txt'))
samples=np.arange(0,len(X),101)
pred=L.Old.predict_raw(X[samples],*(c['structure'].model_arrays[k] for k in L.Old.TREE_KEYS))
ref=booster.predict(X[samples],raw_score=True,num_iteration=24,num_threads=1)
error=float(np.max(np.abs(pred-ref)));assert error<1e-10
checks=[]
for placement in (0,1):
    batch=L.Executable(setup,X,c,placement);result=batch.batch(mixed)
    exe=L.Executable(setup,X,c,placement);accepted=fp=fn=0
    for row in mixed:
        yes,h,hit,used=exe.probe(row)
        if yes:
            accepted+=1
            if not setup.y[row]:fp+=1;exe.insert(h)
        elif setup.y[row]:fn+=1
    assert (accepted,fp,fn)==tuple(map(int,result[:3]))
    assert fn==0
    checks.append(f'placement{placement}: stepwise backend-feedback API matches fused live kernel')
E.save(E.ROOT/'evidence'/'live-pipeline-tests.json',dict(status='passed',raw_score_max_error=error,checks=checks,scope='Actual URL-data component regression, not a performance result'))
print('PASS',checks,flush=True)

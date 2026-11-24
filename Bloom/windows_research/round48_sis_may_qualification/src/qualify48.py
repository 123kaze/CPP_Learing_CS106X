import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data48 import *
from types import SimpleNamespace


def diagnose(seed):
    check();start=time.perf_counter();path=ROOT/'cache/sis_may_prefix.npz';meta=json.loads((ROOT/'results/data.json').read_text());assert sha(path)==meta['prepared_sha256']
    out=ROOT/f'results/seed{seed}_diagnostic.json';assert not out.exists()
    with np.load(path,allow_pickle=False) as d:ids,y,X,first,trace,order,boundary,p1,p2=[d[k] for k in ('ids','y','X','first','trace','order','boundary','prefix1_reject','prefix2_reject')]
    u=(E5.C.splitmix64(ids^np.uint64(seed))>>np.uint64(11)).astype(float)/2**53;early=first<int(boundary)
    sp=dict(member_train=y&(u<.5),neg_train=(~y)&early&(u<.1),neg_val=(~y)&early&(u>=.1)&(u<.2));sp['neg_test']=(~y)&~(sp['neg_train']|sp['neg_val'])
    position=np.full(len(ids),-1,np.int64);position[sp['neg_test']]=np.arange(sp['neg_test'].sum());q=position[trace]
    learn=q[(q>=0)&(order<int(boundary))];tail=q[(q>=0)&(order>=int(boundary))]
    row=dict(status='complete',seed=seed,members=int(y.sum()),negative_pool=int(sp['neg_test'].sum()),train_negative_keys=int(sp['neg_train'].sum()),validation_negative_keys=int(sp['neg_val'].sum()),learning_queries=len(learn),tail_queries=len(tail),development_auc16=None,learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),model_diagnostic_s=0.)
    count=np.bincount(learn,minlength=int(sp['neg_test'].sum()));row['learning_repeat_fraction']=1-float((count>0).sum())/len(learn) if len(learn) else 0.
    feat=np.ascontiguousarray(X).view(np.dtype((np.void,20*4))).ravel();row['query_feature_overlap_fraction']=float(np.isin(feat[sp['neg_test']],feat[y]).mean()) if sp['neg_test'].any() else 0.
    row['cheap_prefix1_tail_rejects']=int(p1[sp['neg_test']][tail].sum());row['cheap_prefix2_tail_rejects']=int(p2[sp['neg_test']][tail].sum())
    if sp['neg_train'].any() and sp['neg_val'].any() and sp['member_train'].any() and (y&~sp['member_train']).any():
        t=time.perf_counter();use=sp['member_train']|sp['neg_train']
        model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[use],label=y[use]),num_boost_round=16)
        score=model.predict(X,raw_score=True,num_threads=1);held=(y&~sp['member_train'])|sp['neg_val'];row['development_auc16']=W.auc(y[held],score[held]);row['actual_diagnostic_trees']=model.num_trees();row['model_diagnostic_s']=time.perf_counter()-t
        cuts=np.unique(np.quantile(score[sp['neg_val']],[.2,.4,.6,.8]));regions=np.searchsorted(cuts,score[sp['neg_test']],side='right');details=[]
        for g in range(len(cuts)+1):
            c=count[regions==g];n=int(c.sum());d=int((c>0).sum());details.append(dict(region=g,learning_queries=n,distinct=d,repeat_fraction=1-d/n if n else None))
        good=[d['repeat_fraction'] for d in details if d['distinct']>=50 and d['repeat_fraction'] is not None];gap=max(good)-min(good) if len(good)>=2 else None
        row.update(regions=details,qualified_repeat_gap=gap,interesting_flag=bool(row['development_auc16']>=.70 and row['query_feature_overlap_fraction']>=.01 and row['learning_repeat_fraction']>=.10 and gap is not None and gap>=.10))
    row.update(wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    assert row['peak_rss_bytes']<=4*1024**3,'Diagnostic RSS cap; no automatic restart'
    save(out,row);check();print('MAY_DIAGNOSTIC_COMPLETE',seed,row['development_auc16'],flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('seed',type=int,choices=SEEDS);a=p.parse_args()
    try:diagnose(a.seed)
    except Exception as e:save(ROOT/f'results/seed{a.seed}.failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300]));raise

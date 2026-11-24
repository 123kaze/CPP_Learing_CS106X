import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data44 import *


def qualify(cluster):
    frozen=check();start=time.perf_counter();meta=parse(cluster);path=ROOT/f'cache/{cluster}.npz';outpath=ROOT/f'results/{cluster}_qualification.json';assert not outpath.exists()
    diagnostics=[];reasons=[]
    if meta['members']<1000:reasons.append('members<1000')
    if meta['distinct_negative_keys']<1000:reasons.append('negative_keys<1000')
    for seed in SEEDS:
        t=time.perf_counter();s,X,learn,tail=prepare(path,seed);sp=s.split
        row=dict(seed=seed,members=len(s.h1m),negative_pool=len(s.h1q),train_negatives=int(sp['neg_train'].sum()),validation_negatives=int(sp['neg_val'].sum()),learning_negatives=len(learn),tail_negatives=len(tail),learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),budgets_kib=budgets(len(s.h1m)),diagnostic_reasons=[])
        for field,limit in (('train_negatives',20),('validation_negatives',20),('learning_negatives',1000),('tail_negatives',1000)):
            if row[field]<limit:reasons.append(f'seed{seed}:{field}<{limit}')
        feat=X.view(np.dtype((np.void,24*4))).ravel();row['query_feature_overlap_fraction']=float(np.isin(feat[sp['neg_test']],feat[s.y]).mean()) if len(s.h1q) else 0.
        freq=np.bincount(learn,minlength=len(s.h1q));row['learning_repeat_fraction']=1-float((freq>0).sum())/len(learn) if len(learn) else 0.
        if sp['member_train'].any() and sp['neg_train'].any() and sp['neg_val'].any():
            use=sp['member_train']|sp['neg_train'];tt=time.perf_counter()
            model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[use],label=s.y[use]),num_boost_round=16)
            score=model.predict(X,raw_score=True,num_threads=1);held=(s.y&~sp['member_train'])|sp['neg_val'];row['development_auc16']=W.auc(s.y[held],score[held]);row['model_diagnostic_s']=time.perf_counter()-tt
            cuts=np.unique(np.quantile(score[sp['neg_val']],[.2,.4,.6,.8]));reg=np.searchsorted(cuts,score[sp['neg_test']],side='right');regions=[]
            for g in range(len(cuts)+1):
                f=freq[reg==g];q=int(f.sum());d=int((f>0).sum());regions.append(dict(region=g,learning_queries=q,learning_distinct=d,repeat_fraction=1-d/q if q else None))
            eligible=[r['repeat_fraction'] for r in regions if r['learning_distinct']>=50 and r['repeat_fraction'] is not None]
            gap=max(eligible)-min(eligible) if len(eligible)>=2 else None;row.update(regions=regions,qualified_region_repeat_gap=gap)
            row['interesting_diagnostic_flag']=bool(row['development_auc16'] is not None and row['development_auc16']>=.70 and row['query_feature_overlap_fraction']>=.01 and row['learning_repeat_fraction']>=.10 and gap is not None and gap>=.10)
        else:row.update(development_auc16=None,interesting_diagnostic_flag=False)
        row['wall_s']=time.perf_counter()-t;diagnostics.append(row)
    out=dict(status='complete',cluster=cluster,freeze_sha256=frozen,eligible_for_method_comparison=not reasons,ineligibility_reasons=reasons,diagnostics=diagnostics,diagnostic_flags_do_not_select_clusters=True,method_FP_not_measured=True,task=meta['task'],wall_s=time.perf_counter()-start)
    save(outpath,out);check();print('QUALIFIED',cluster,not reasons,'reasons',reasons,'AUC',[r['development_auc16'] for r in diagnostics],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('cluster',choices=CLUSTERS);a=p.parse_args()
    try:qualify(a.cluster)
    except Exception as e:save(ROOT/f'results/{a.cluster}_qualification.failure.json',dict(status='failed',error=repr(e)));raise

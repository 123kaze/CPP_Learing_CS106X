import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare50 import *


def run(seed):
    check();start=time.perf_counter();target=ROOT/f'results/seed{seed}.json';assert not target.exists()
    meta=json.loads((ROOT/'results/preparation.json').read_text());assert sha(ROOT/'cache/sis_fullfile.npz')==meta['prepared_sha256']
    t=time.perf_counter();ids,y,X,sp,learn,tail,rules=load(seed);load_s=time.perf_counter()-t
    train=sp['member_train']|sp['neg_train'];held=(y&~sp['member_train'])|sp['neg_val'];assert not np.any(train&held)
    row=dict(status='running',seed=seed,members=int(y.sum()),train_members=int(sp['member_train'].sum()),train_negative_keys=int(sp['neg_train'].sum()),validation_negative_keys=int(sp['neg_val'].sum()),query_negative_keys=int(sp['neg_test'].sum()),learning_queries=len(learn),tail_queries=len(tail),load_s=load_s,development_auc16=None,learning_sha256=W.ah(learn),tail_sha256=W.ah(tail))
    t=time.perf_counter();lf=np.bincount(learn,minlength=int(sp['neg_test'].sum()));tf=np.bincount(tail,minlength=len(lf));row['learning_repeat_fraction']=1-float((lf>0).sum())/len(learn) if len(learn) else 0.
    row['tail_unseen_query_fraction']=float(tf[lf==0].sum())/len(tail) if len(tail) else None;row['tail_distinct_keys']=int((tf>0).sum());row['tail_unseen_distinct_keys']=int(((tf>0)&(lf==0)).sum());row['count_s']=time.perf_counter()-t
    t=time.perf_counter();features=np.ascontiguousarray(X).view(np.dtype((np.void,80))).ravel();row['query_feature_overlap_fraction']=float(np.isin(features[sp['neg_test']],features[y]).mean());row['overlap_s']=time.perf_counter()-t
    row['cheap_prefix1_tail_rejects']=int(rules[0][sp['neg_test']][tail].sum());row['cheap_prefix2_tail_rejects']=int(rules[1][sp['neg_test']][tail].sum())
    if sp['neg_train'].any() and sp['neg_val'].any() and sp['member_train'].any():
        t=time.perf_counter();model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[train],label=y[train]),num_boost_round=16);row['training_s']=time.perf_counter()-t
        t=time.perf_counter();score=model.predict(X,raw_score=True,num_threads=1);row['score_s']=time.perf_counter()-t
        t=time.perf_counter();row['development_auc16']=W.auc(y[held],score[held]);row['actual_trees']=model.num_trees();row['auc_s']=time.perf_counter()-t
        probability=1/(1+np.exp(-score));segments=E5.D.segment_of(probability)
        row['segment_resolution']=dict(member_occupied_bins=len(np.unique(segments[y])),validation_negative_occupied_bins=len(np.unique(segments[sp['neg_val']])),query_negative_occupied_bins=len(np.unique(segments[sp['neg_test']])),member_fraction_in_bin999=float((segments[y]==999).mean()),validation_negative_fraction_in_bin999=float((segments[sp['neg_val']]==999).mean()),member_raw_score_quantiles=np.quantile(score[y],[0,.5,1]).tolist(),validation_negative_raw_score_quantiles=np.quantile(score[sp['neg_val']],[0,.5,1]).tolist())
        cuts=np.unique(np.quantile(score[sp['neg_val']],[.2,.4,.6,.8]));reg=np.searchsorted(cuts,score[sp['neg_test']],side='right');regions=[]
        for g in range(len(cuts)+1):
            f=lf[reg==g];n=int(f.sum());d=int((f>0).sum());regions.append(dict(region=g,learning_queries=n,distinct=d,repeat_fraction=1-d/n if n else None))
        good=[x['repeat_fraction'] for x in regions if x['distinct']>=50 and x['repeat_fraction'] is not None];gap=max(good)-min(good) if len(good)>=2 else None
        row.update(regions=regions,qualified_repeat_gap=gap,interesting_flag=bool(row['development_auc16']>=.7 and row['query_feature_overlap_fraction']>=.01 and row['learning_repeat_fraction']>=.1 and gap is not None and gap>=.1))
    row.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,method_FP_measured=False,score_direction_flipped=False,class_weights_changed=False)
    assert row['peak_rss_bytes']<=4*1024**3;save(target,row);check();print('FULLFILE_DEV_COMPLETE',seed,row['development_auc16'],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('seed',type=int,choices=SEEDS);a=p.parse_args()
    try:run(a.seed)
    except Exception as e:save(ROOT/f'results/seed{a.seed}.failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300]));raise

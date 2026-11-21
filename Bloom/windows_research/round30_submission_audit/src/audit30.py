"""Reproduce source-audit numbers and search a bounded, prespecified no-repeat counterexample."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round27_http_real/src'))
from worker27 import E5,ra5,ra6,prepare,summarize19,prefix_raw_scores,model_arrays,ah
from data27 import save,sha
import lightgbm as lgb
import numpy as np
import json
import csv
import time


def csvrows(p):
    with p.open() as f:return list(csv.DictReader(f))


def numeric():
    backend=[]
    for ds in ('caida_256','cod_1024'):
        p=WR/f'round6_bucket/results/e789/{ds}.json';d=json.loads(p.read_text())
        for variant,m in d['e8'].items():
            for method,r in m.items():backend.append(dict(setting=ds,backend=variant,method=method,us_per_query=r['ns_per_query']/1000,backend_calls=r['backend_calls'],members_found=r['members_found'],ratio_to_NoFilter=r['ns_per_query']/m['NoFilter']['ns_per_query'],source_sha256=sha(p)))
    d=json.loads((WR/'round6_bucket/results/e10.json').read_text());sensitivity=[dict(case=r['case'],learning_share=r['value'],ra_fp=r['RA6']['fp'],replay_fp=r['LearnGrid']['fp'],nonworse=r['RA6']['fp']<=r['LearnGrid']['fp']) for r in d if r['variable']=='learning_share']
    assert len(sensitivity)==16 and sum(r['nonworse'] for r in sensitivity)==13
    timing=[r for r in csvrows(WR/'round15_learning_scaling_v2/results/timing_rows.csv') if int(r['L'])==100000000]
    memory=[{k:r[k] for k in ('method','rep','learning_trace_bytes','learning_state_bytes','count_state_bytes','peak_rss_bytes')} for r in timing]
    assert all(int(r['learning_trace_bytes'])==800000000 for r in memory)
    ratios=[];allrows=csvrows(WR/'round19_gt_fix/results/updated_main_comparisons.csv')
    for mode in ('index','fp64'):
        eligible=[r for r in allrows if r['cache']==mode and r['cohort']=='main' and r['included']=='True' and r['workload']!='探测重放10%'];assert len(eligible)==748
        for cohort,rows in [('all',eligible),('repeated',[r for r in eligible if r['workload'] not in ('每key一次','全新对抗')])]:
            v=np.array([(int(r['repaired_ra_fp'])+1)/(int(r['gama_fp'])+1) for r in rows]);ratios.append(dict(cache=mode,cohort=cohort,cases=len(rows),median_RA_Gama=float(np.median(v)),inverse_median=float(1/np.median(v)),median_Gama_RA=float(np.median(1/v))))
    gt=summarize19(np.array([0,1,1],np.int64));effective=dict(sequence='a,b,b',rates=gt.rate.tolist(),seen_mass=float(gt.rate.sum()),unseen_mass=gt.N1/gt.L,total=float(gt.rate.sum()+gt.N1/gt.L));assert np.isclose(effective['total'],4/3)
    save(ROOT/'results/numeric_audit.json',dict(backend=backend,sensitivity=sensitivity,memory=memory,ratios=ratios,gt_example=effective))
    print('NUMERIC VERIFIED: SQLite raw rows,13/16 sensitivity,800MB trace,GT4/3',flush=True)


def search():
    out=ROOT/'results/no_repeat_search.json';assert not out.exists()
    records=[];start=time.perf_counter()
    for ds in ('nasa_jul95','nasa_aug95'):
        for seed in (2701,2702,2703):
            s,X,learn,tail=prepare(WR/f'round27_http_real/cache/{ds}.npz',seed);s.name+='__audit30';sp=s.split
            train=sp['member_train']|sp['neg_train']
            model=lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),lgb.Dataset(X[train],label=s.y[train]),num_boost_round=200)
            scores=prefix_raw_scores(model,X,E5.TREES)
            for t in E5.TREES:E5.R._MODEL_ARRAYS[s.name,t]=model_arrays(model,t)
            unique=np.unique(learn);lm=summarize19(unique);assert lm.N1==lm.L and np.all(lm.rate==0)
            for kib in (4,8,16):
                cands=E5.candidates(s,scores,kib);g=E5.gama(cands);r,info=ra6.select6(s,scores,lm,kib,len(tail))
                table=ra5.candidate_table(s,scores,lm,kib,len(tail),ra5.Config(new_mix=0.))
                same_config=(g['trees'],g['cache_bytes'])==(r['trees'],r['cache_bytes'])
                same_flags=np.array_equal(g['structure'].fp_static,r['structure'].fp_static)
                same_structure=same_config and all(np.array_equal(getattr(g['structure'],k),getattr(r['structure'],k)) for k in ('b','m','k','kind'))
                summary=dict(dataset=ds,seed=seed,budget_kib=kib,learning_distinct_once=len(unique),H=len(tail),gama_trees=g['trees'],gama_frac=g['frac'],ra_trees=r['trees'],ra_frac=r['frac'],same_config=same_config,same_structure=same_structure,same_static_flags=same_flags,
                             gama_static_flags_sha256=ah(g['structure'].fp_static),ra_static_flags_sha256=ah(r['structure'].fp_static),ra_info=info)
                records.append(summary)
                print('NO_REPEAT',ds,seed,kib,'Gama',g['trees'],g['frac'],'RA',r['trees'],r['frac'],'same',same_structure,flush=True)
                if not same_structure:
                    candidates=[]
                    for row in table:
                        c=next(c for c in cands if (c['trees'],c['frac'])==(row['trees'],row['frac']))
                        td=E5.tree(s,scores,c['trees']);b,f,e=E5.D.allocate(td.g,td.v+1.,(kib*1024-td.fixed-c['cache_bytes'])*8)
                        reg=E5.D.region_of_segment(b);nr=np.bincount(reg,weights=td.g,minlength=5)
                        candidates.append(dict(trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes'],gama_est_fpr=c['structure'].est_fpr,
                                               ra_stage1_normalized=row['pred']/len(tail),raw_allocator_est_fpr=e,empty_region_validation_mass=float(td.h[nr[reg]==0].sum()),
                                               bounds=b.tolist(),region_fpr=f.tolist(),region_members=nr.tolist(),weights_identical_Gama=bool(np.array_equal(row['weights'],td.v+1.))))
                    model.save_model(str(ROOT/'results/counterexample_model.txt'))
                    save(out,dict(status='counterexample_found',searched=records,first_counterexample=summary,candidates=candidates,model_sha256=sha(ROOT/'results/counterexample_model.txt'),input_sha256=sha(WR/f'round27_http_real/cache/{ds}.npz'),wall_s=time.perf_counter()-start,
                                  scope='New real-data-derived no-repeat construction; does NOT show any of the archived140cases were wrong. No evaluation-tail FP used for counterexample search.'))
                    return
            E5._TREE.clear();E5.R._MODEL_ARRAYS.clear();E5.R._GSETUPS.clear()
    save(out,dict(status='none_found_in_prespecified18settings',searched=records,wall_s=time.perf_counter()-start,scope='Finite negative search result, not proof of universal equivalence.'))


def main():
    files={Path(__file__),ROOT/'plan/design-freeze.md',*list((WR/'round27_http_real/src').glob('*.py'))}
    for p in ('round5_dp/src/engine5.py','round5_dp/src/ra5.py','round5_dp/src/dp_alloc.py','round6_bucket/src/ra6.py','round6_bucket/src/e789.py','round19_gt_fix/src/summarize19.py'):files.add(WR/p)
    freeze=ROOT/'plan/freeze.json';assert not freeze.exists()
    save(freeze,dict(date='2026-11-21',paper_version='e256658:vldb',sources={str(p.relative_to(BLOOM)):sha(p) for p in sorted(files)}))
    numeric();search()
    for p,h in json.loads(freeze.read_text())['sources'].items():assert sha(BLOOM/p)==h
    save(ROOT/'results/completion.json',dict(status='complete',numeric_audit=True,no_repeat_search=True,freeze_sha256=sha(freeze)))


if __name__=='__main__':main()

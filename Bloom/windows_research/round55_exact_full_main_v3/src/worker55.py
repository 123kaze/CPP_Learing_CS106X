"""Fresh exact-key execution of each archived case; all tail diagnostics remain outside selection."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common55 import *


def run(ds,kib,pilot=False):
    start=time.perf_counter();manifest=case_manifest();setting=next(x for x in manifest['settings'] if x['dataset']==ds and x['budget_kib']==kib)
    cases=setting['cases'];tag=('pilot_' if pilot else '')+f'{ds}_{kib}';folder=ROOT/'results'/tag
    reuse=json.loads((ROOT/'plan/reuse.json').read_text());allowed={r['target']:r for r in reuse['files']};reused_s=0.;reused_count=0
    if folder.exists():
        assert pilot and tag=='pilot_caida_128' and not (folder/'status.json').exists()
        for p in folder.iterdir():
            rel=str(p.relative_to(ROOT));assert rel in allowed and sha(p)==allowed[rel]['sha256'];assert p.name.startswith('case_')
    else:folder.mkdir(parents=True)
    if pilot and not ds.endswith('_flow'):cases=[c for c in cases if c['seed']==0 and c['workload'] in ('每key一次','uniform-全部','zipf1.0-全部')];assert len(cases)==3
    d=load(ds);s=d.s;scores=d.scores;records=[];meta=dict(status='running',pilot=pilot,dataset=ds,budget_kib=kib,cases_expected=len(cases),input=d.meta,case_files=[])
    specs=dict(E5.workload_specs(len(s.h1q))) if not ds.endswith('_flow') else {'真实轨迹':None}
    with scope(d.cache):
        grid=[];cost={};t=time.perf_counter()
        for tr in E5.TREES:
            for frac in E5.FRACS:
                c,seconds=timed(E5.build,s,scores,tr,kib,frac)
                if c is not None:grid.append(c);cost[tr,frac]=seconds
        grid_s=time.perf_counter()-t;g=E5.gama(grid);by={(c['trees'],c['frac']):c for c in grid};g_s=sum(v for (tr,fr),v in cost.items() if fr==0)
        bgrid=[];bfcost=[]
        for frac in E5.FRACS:c,tm=timed(BF.build,s,kib,frac,d.cache);bgrid.append(c);bfcost.append(tm)
        stack_bases={};t=time.perf_counter()
        for frac in STACK.X7.FRACS:
            side=int(kib*1024*frac);c=E5.build(s,scores,g['trees'],kib,0.,cache_bytes=side,slots=0)
            if c is not None:stack_bases[frac]=(side,c)
        stack_base_s=time.perf_counter()-t
        meta.update(grid_build_s=grid_s,bf_grid_build_s=sum(bfcost),stack_shared_base_build_s=stack_base_s,candidates=len(grid));save(folder/'status.json',meta)
        for ci,case in enumerate(cases):
            prior=folder/f'case_{ci:03d}.json'
            if prior.exists():
                assert pilot and tag=='pilot_caida_128';r=allowed[str(prior.relative_to(ROOT))];assert sha(prior)==r['sha256']
                previous=json.loads(prior.read_text());assert previous['status']=='complete' and previous['case']==case and previous['regression53']
                reused_s+=previous['wall_s'];reused_count+=1;meta['case_files'].append(prior.name)
                print('PILOT_CASE_REUSED',tag,ci,r['sha256'],flush=True);continue
            ct=time.perf_counter();name=case['workload'];seed=case['seed'];base,stream_s=timed(E5.base_stream,s,name,specs[name],seed,10000000);n=len(base)//4;learn,base_tail=base[:n],base[n:];H=len(base_tail)
            lm,summary_s=timed(summarize19,learn);(rep,replog),replay_s=timed(d.e.best,grid,learn);(bf,bflog),breplay_s=timed(d.e.best,bgrid,learn)
            table,table_s=timed(RA.candidate_table,s,scores,lm,kib,H,RA.Config(new_mix=0.));short=sorted(table,key=lambda r:(r['pred'],r['trees'],r['frac']))[:10];built=[]
            for rank,r in enumerate(short):
                t=time.perf_counter();c=E5.build(s,scores,r['trees'],kib,r['frac'],weights=r['weights'],cache_bytes=r['cache_bytes'],slots=r['slots']);build_s=time.perf_counter()-t;t=time.perf_counter()
                pred=R6.bucket_prediction(s,lm,E5.tree(s,scores,r['trees']),c,H,r['seg_fpr_pred']);refine_s=time.perf_counter()-t
                built.append(dict(candidate=c,stage1=r['pred'],stage2=pred,rank=rank,build_s=build_s,refine_s=refine_s))
            choices={'Gama':(g,g_s,{}),'Gama+10%':(by[g['trees'],.1],g_s+cost[g['trees'],.1],{}),'Replay':(rep,grid_s+replay_s,{}),'RA-stage1':(built[0]['candidate'],summary_s+table_s+built[0]['build_s'],dict(pred=built[0]['stage1'])),'PlainBF':(bgrid[0],bfcost[0],{}),'BF+Exact':(bf,sum(bfcost)+breplay_s,{})}
            for label,top in (('RA6-top3',3),('RA6',5),('RA6-top10',10)):
                r=min(built[:top],key=lambda x:(x['stage2'],x['rank']));tm=summary_s+table_s+sum(a['build_s']+a['refine_s'] for a in built[:top]);choices[label]=(r['candidate'],tm,dict(pred=r['stage2'],rank=r['rank'],built=min(top,len(built))))
            (glob,gi),gt=timed(RA.select,s,scores,lm,kib,H,RA.Config(mode='global',new_mix=0.));choices['RA-global']=(glob,summary_s+gt,gi)
            rowout=[]
            for method in MAIN:
                c,seconds,info=choices[method];tail=tail_for(c,name,base_tail,seed);evalout=evaluate(d,c,tail)
                if method=='Gama':assert evalout['fp']==case['historical_Gama_fp'] and c['trees']==case['historical_Gama_trees'],'No-cache historical regression'
                rowout.append(dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,method=method,phase='cold',trees=c['trees'],frac=c['frac'],selection_build_s=seconds,flags_sha=ah(c['structure'].fp_static),tail_queries=H,selection_info=info,**ledger(c),**evalout))
            for method in ('RA6','Replay','BF+Exact'):
                c,seconds,info=choices[method];tail=tail_for(c,name,base_tail,seed)
                rowout.append(dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,method=method+'-warm',phase='warm',trees=c['trees'],frac=c['frac'],selection_build_s=seconds,flags_sha=ah(c['structure'].fp_static),tail_queries=H,selection_info=info,**ledger(c),**evaluate(d,c,tail,warm=learn)))
            # Learned stacked has no negative cache: retain its original BF-layer semantics.
            t=time.perf_counter();stack_flags,stack_frac,stack_b2,stack_bytes=STACK.stacked_fp(s,stack_bases,g,kib,learn);stack_s=time.perf_counter()-t;assert stack_bytes<=kib*1024
            toy=dict(structure=SimpleNamespace(fp_static=stack_flags));stail=tail_for(toy,name,base_tail,seed);fp=int(stack_flags[stail].sum())
            if 'historical_stacked_fp' in case:assert fp==case['historical_stacked_fp'],'Paper-baseline stacked regression'
            rowout.append(dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,method='Learned-stacked',phase='learned-negative-layers',trees=g['trees'],frac=stack_frac,fp=fp,total_bytes=int(stack_bytes),budget_bytes=kib*1024,member_index_bytes=0,member_fn=0,selection_build_s=stack_s+stack_base_s+g_s,tail_queries=H,flags_sha=ah(stack_flags),layers=dict(frac=stack_frac,b2=stack_b2,baseline_source='frozen round6 stacked_full.stacked_fp'),historical_stacked_regression='historical_stacked_fp' in case))
            del stack_flags
            ablations=[]
            if seed<=2:
                for label,cfg in ABLS.items():
                    lmv=lm if cfg.gt else summarize19(learn,False);(c,info),tm=timed(RA.select,s,scores,lmv,kib,H,cfg);tail=tail_for(c,name,base_tail,seed)
                    ablations.append(dict(variant=label,trees=c['trees'],frac=c['frac'],selection_build_s=tm,selection_info=info,flags_sha=ah(c['structure'].fp_static),**ledger(c),**evaluate(d,c,tail)))
                (c,info),tm=timed(table_variant,d,lm,kib,H);ablations.append(dict(variant='Table-exact-adapter',trees=c['trees'],frac=c['frac'],selection_build_s=tm,selection_info=info,flags_sha=ah(c['structure'].fp_static),**ledger(c),**evaluate(d,c,tail_for(c,name,base_tail,seed))))
            oracle=None;oracle_detail=[]
            if seed<=2:
                for c in grid:
                    t=time.perf_counter();cnt,_=d.e.evaluate(c,tail_for(c,name,base_tail,seed));value=int(cnt[0]);oracle_detail.append(dict(trees=c['trees'],frac=c['frac'],fp=value,tail_replay_s=time.perf_counter()-t))
                oracle=min(r['fp'] for r in oracle_detail)
            ranks=[]
            for b in built:
                c=b['candidate'];cnt,_=d.e.evaluate(c,tail_for(c,name,base_tail,seed));ranks.append(dict(rank=b['rank'],trees=c['trees'],frac=c['frac'],stage1=b['stage1'],stage2=b['stage2'],fp=int(cnt[0])))
            full=[]
            if seed==0:
                for r in table:
                    c=E5.build(s,scores,r['trees'],kib,r['frac'],weights=r['weights'],cache_bytes=r['cache_bytes'],slots=r['slots'])
                    p2=R6.bucket_prediction(s,lm,E5.tree(s,scores,c['trees']),c,H,r['seg_fpr_pred']);cnt,_=d.e.evaluate(c,tail_for(c,name,base_tail,seed))
                    full.append(dict(trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes'],stage1=r['pred'],stage2=p2,fp=int(cnt[0])))
            # Frozen53 7-method regression for matching fixed seed0 cases (not all seeds/loads).
            regression=False
            if seed==0 and name in ('每key一次','uniform-全部','zipf1.0-全部','真实轨迹'):
                prior=WR/f'round53_index_free_recheck_v4/results/{ds}_{kib}.json'
                if prior.exists():
                    rr=json.loads(prior.read_text())['rows'];mapm={'RA6':'RA-PLBF-GT19','BF+Exact':'BF+Exact','RA-global':'RA-global'}
                    for row in rowout:
                        if row['phase']!='cold' or row['method'] in ('RA-stage1','RA6-top3','RA6-top10'):continue
                        old=next(x for x in rr if x['method']==mapm.get(row['method'],row['method']) and x['workload']==name)
                        assert (row['trees'],row['frac'],row['fp'],row['flags_sha'],row['cache_sha'],row['total_bytes'])==(old['trees'],old['frac'],old['fp'],old['static_flags_sha256'],old['cache_sha256'],old['total_bytes'])
                    regression=True
            out=dict(status='complete',case=case,rows=rowout,ablations=ablations,learning_queries=n,tail_queries=H,learning_sha=ah(learn),base_tail_sha=ah(base_tail),stream_generation_s=stream_s,summary_s=summary_s,learning_count_payload_bytes=lm.keys.nbytes+lm.counts.nbytes,learning_count_rate_physical_bytes=sum(sys.getsizeof(x) for x in (lm.keys,lm.counts,lm.rate)),learning_trace_logical_bytes=learn.nbytes,full_trace_retained_bytes=base.nbytes,learning_Replay_records=replog,learning_BF_records=bflog,hindsight_h_fp=oracle,hindsight_h_records=oracle_detail,top10=ranks,weighted_full=full,regression53=regression,wall_s=time.perf_counter()-ct)
            filename=f'case_{ci:03d}.json';save(folder/filename,out);meta['case_files'].append(filename);save(folder/'status.json',meta)
            print('CASE_COMPLETE',tag,ci+1,'/',len(cases),name,seed,'seconds',round(out['wall_s'],3),flush=True)
            del table,built,choices,glob,base,learn,base_tail,full,oracle_detail
    freeze_check();elapsed=time.perf_counter()-start;meta.update(status='complete',cases_completed=len(cases),wall_s=elapsed+reused_s,new_worker_wall_s=elapsed,reused_pilot_cases=reused_count,reused_case_wall_s=reused_s,pilot_wall_scope='new worker measured time plus explicitly reused case times' if reused_count else 'measured current worker wall',peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    assert meta['peak_rss_bytes']<4*1024**3;save(folder/'status.json',meta);print('WORKER_COMPLETE',tag,meta['wall_s'],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('kib',type=int);p.add_argument('--pilot',action='store_true');a=p.parse_args();run(a.dataset,a.kib,a.pilot)

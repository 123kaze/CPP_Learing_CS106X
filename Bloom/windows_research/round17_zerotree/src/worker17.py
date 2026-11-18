"""One dataset/cache per process, no algorithm mutation across cache formats."""
from common17 import *
import sys
import time
import platform
import traceback
import argparse
import csv
import numpy as np
import zero17 as Z
from native_zero17 import ZeroTreeFilter,verify_negative_stream
E5=Z.E5


def reference_rows(ds,mode):
    with (WR/'round13_complete/results/combined_baseline_rows.csv').open() as f:
        rows=[r for r in csv.DictReader(f) if r['dataset']==ds and r['cache']==mode]
    return {(int(r['budget_kib']),r['workload'],int(r['seed'])):r for r in rows}


def evaluate(c,tail,setup,safe,mode):
    if c['cache_bytes'] and mode=='fp64':
        r=E5.K.simulate(tail,setup.h1q,None,c['structure'].fp_static,c['cache_bytes'],member_hashes=setup.member_hashes)
        assert r['member_hits_final']==0
        return r
    if c['cache_bytes']:
        r=E5.K.simulate(tail,setup.h1q,safe,c['structure'].fp_static,c['cache_bytes'])
        return r
    return dict(fp=int(c['structure'].fp_static[tail].sum()),hits=0,inserts=0,evictions=0)


def main(a):
    out=dict(status='running',dataset=a.dataset,cache=a.cache,results=[],pilot=a.pilot)
    try:
        if a.dataset in TCP:
            sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
        E5.K=Z.BF.CACHES[a.cache]
        start=time.perf_counter();setup,scores,safe=E5.load(a.dataset)
        out['input_prepare_s']=time.perf_counter()-start
        refs=reference_rows(a.dataset,a.cache)
        matrix=cases(a.dataset)
        if a.pilot:matrix=matrix[:1]
        specmap=dict(E5.workload_specs(len(setup.h1q))) if a.dataset not in TCP else {'真实轨迹':None}
        jobs={k:[] for k,_,_,_ in matrix}
        for case in matrix:jobs[case[0]].append(case)
        for kib,items in jobs.items():
            start=time.perf_counter()
            learned=E5.candidates(setup,scores,kib)
            learned_build_s=time.perf_counter()-start
            start=time.perf_counter();zeros=[Z.BF.build(setup,kib,f,E5.K) for f in E5.FRACS]
            zero_build_s=time.perf_counter()-start
            gam=E5.gama(learned)
            for _,name,seed,cohort in items:
                base=E5.base_stream(setup,name,specmap[name],seed,queries=10_000_000)
                n=len(base)//4;learn,tail=base[:n],base[n:]
                assert n>0
                ref=refs[kib,name,seed]
                assert ah(base)==ref['base_stream_sha256'] and len(tail)==int(ref['tail_len'])
                t=time.perf_counter();lm=Z.RA.ra4.summarize(learn,True);summarize_s=time.perf_counter()-t
                old,old_info=Z.ra6.select6(setup,scores,lm,kib,len(tail))
                new,info=Z.select(setup,scores,lm,kib,len(tail))
                zero,zi=Z.select(setup,None,lm,kib,len(tail),trees=())
                if a.pilot:
                    disabled,di=Z.select(setup,scores,lm,kib,len(tail),include_zero=False)
                    assert (old['trees'],old['frac'])==(disabled['trees'],disabled['frac'])
                    assert old_info['predicted_fp']==di['predicted_fp']
                    assert np.array_equal(old['structure'].fp_static,disabled['structure'].fp_static)
                    out['disabled_zero_reproduces_frozen_ra6']=True
                t=time.perf_counter();bf,bffps=E5.replay_best(zeros,learn,setup,safe);bf_select_s=time.perf_counter()-t
                t=time.perf_counter();replay,rfps=E5.replay_best(learned,learn,setup,safe);replay_s=time.perf_counter()-t
                t=time.perf_counter();expanded,xfps=E5.replay_best(learned+zeros,learn,setup,safe);expanded_s=time.perf_counter()-t
                bfp=bffps[bf['trees'],bf['frac']][0];rfp=rfps[replay['trees'],replay['frac']][0]
                xfp,cut=xfps[expanded['trees'],expanded['frac']]
                assert not cut and xfp<=min(bfp,rfp),'Expanded Replay must not worsen its training objective'
                choices={'RA6-Z':new,'RA6':old,'Zero-Predict':zero,'Gama':gam,'BF':zeros[0],
                         'BF+ReplayCache':bf,'Replay':replay,'Replay+Z':expanded}
                times={'RA6-Z':summarize_s+info['select_s'],'RA6':summarize_s+old_info['select_seconds'],
                       'Zero-Predict':summarize_s+zi['select_s'],'Gama':0.,'BF':0.,
                       'BF+ReplayCache':bf_select_s,'Replay':replay_s,'Replay+Z':expanded_s}
                entry=dict(dataset=a.dataset,cache=a.cache,budget_kib=kib,workload=name,seed=seed,cohort=cohort,
                           learning_queries=n,tail_len=len(tail),distinct_learning_keys=len(lm.keys),
                           base_stream_sha256=ah(base),tail_stream_sha256=ah(tail),zero_info=info,zero_only_info=zi,
                           old_ra6_info=old_info,learned_candidates_build_s=learned_build_s,zero_candidates_build_s=zero_build_s,
                           expanded_replay_learn_fp=xfp,old_replay_learn_fp=rfp,bf_replay_learn_fp=bfp,methods={})
                for method,c in choices.items():
                    r=evaluate(c,tail,setup,safe,a.cache);st=c['structure'];assert st.used_bytes<=kib*1024
                    result=dict(trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes'],total_bytes=st.used_bytes,
                                model_bytes=st.model_bytes,fp=int(r['fp']),fpr=r['fp']/len(tail),hits=int(r['hits']),
                                select_s=times[method],static_flags_sha256=ah(st.fp_static),member_checks_passed=True)
                    if c['trees']==0:
                        assert st.model_bytes==0 and st.metadata_bytes==32
                        native=ZeroTreeFilter(st.data,c['cache_bytes'],a.cache,setup.h1m)
                        sp=native.spec
                        fp,hits=verify_negative_stream(native.data,native.state,tail,setup.h1q,native.sorted_members,
                                sp['buckets'],sp['Q'],sp['ob'],sp['slot_bits'],sp['handbits'],a.cache=='fp64')
                        assert fp==r['fp'] and hits==r['hits'],(method,'native-vs-frozen')
                        assert (native.probe_hashes(setup.h1m)==1).all()
                        assert native.deployment_bytes==st.used_bytes
                        result.update(native_zero_checks=True,bf_data_sha256=ah(st.data),metadata_bytes=32,
                                      external_index_bytes=native.external_index_bytes)
                    if method in ('RA6','Gama','BF','BF+ReplayCache','Replay'):
                        key={'RA6':'ra_fp','Gama':'gama_fp','BF':'bf_fp','BF+ReplayCache':'bfcache_fp','Replay':'replay_fp'}[method]
                        assert result['fp']==int(ref[key]),('archive mismatch',a.dataset,kib,name,seed,method,result['fp'],ref[key])
                        result['matches_round13_archive']=True
                    entry['methods'][method]=result
                out['results'].append(entry)
                save(a.output,out)
                print(f'CASE {a.dataset}/{kib} {name} s{seed} {a.cache}: new={entry["methods"]["RA6-Z"]["fp"]} '
                      f't={new["trees"]} frac={new["frac"]} old={entry["methods"]["RA6"]["fp"]} BFcache={entry["methods"]["BF+ReplayCache"]["fp"]}',flush=True)
            del learned,zeros
        assert len(out['results'])==len(matrix)
        out['status']='ok'
    except Exception:
        out['status']='error';out['error']=traceback.format_exc();print(out['error'],flush=True)
    out.update(python=platform.python_version(),numpy=np.__version__)
    save(a.output,out)
    if out['status']!='ok':raise SystemExit(1)
    print(f'COMPLETE {a.dataset} {a.cache}: {len(out["results"])} cases',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=DATASETS,required=True)
    p.add_argument('--cache',choices=('index','fp64'),required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pilot',action='store_true')
    a=p.parse_args()
    if a.output.exists():p.error('Output exists; refusing overwrite')
    main(a)

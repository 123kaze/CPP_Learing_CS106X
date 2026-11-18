"""Compute learning decision first; only then execute identical cold test tails."""
from common20 import *
import argparse
import json
import time
import traceback
import platform
import numpy as np
import guard20 as G
E5=G.E5


def tail_result(c,tail,setup,safe,mode):
    if c['cache_bytes'] and mode=='fp64':
        r=E5.K.simulate(tail,setup.h1q,None,c['structure'].fp_static,c['cache_bytes'],member_hashes=setup.member_hashes)
        assert r['member_hits_final']==0
    else:r=E5.evaluate(c,tail,setup,safe)
    st=c['structure'];assert st.used_bytes<=st.budget_bytes
    out=dict(trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes'],total_bytes=st.used_bytes,
             model_bytes=st.model_bytes,fp=int(r['fp']),hits=int(r['hits']),member_checks_passed=True,
             static_flags_sha256=ah(st.fp_static))
    if c['trees']==0:
        native=G.ZeroTreeFilter(st.data,c['cache_bytes'],mode,setup.h1m);s=native.spec
        fp,hits=G.verify_negative_stream(native.data,native.state,tail,setup.h1q,native.sorted_members,
               s['buckets'],s['Q'],s['ob'],s['slot_bits'],s['handbits'],mode=='fp64')
        assert (fp,hits)==(r['fp'],r['hits'])
        assert (native.probe_hashes(setup.h1m)==1).all()
        assert native.deployment_bytes==st.used_bytes and st.model_bytes==0
        out.update(native_zero_checks=True,external_index_bytes=native.external_index_bytes,
                   bf_buffer_sha256=ah(st.data))
    return out


def main(a):
    out=dict(status='running',dataset=a.dataset,cache=a.cache,pilot=a.pilot,cases=[])
    try:
        if a.dataset in TCP:
            sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
        E5.K=G.BF.CACHES[a.cache]
        setup,scores,safe=E5.load(a.dataset)
        path=WR/f'round17_zerotree/results/main/{a.dataset}_{a.cache}.json'
        old=json.loads(path.read_text());assert old['status']=='ok'
        refs={(r['budget_kib'],r['workload'],r['seed']):r for r in old['results']}
        out['round17_archive_sha256']=digest(path)
        matrix=cases(a.dataset)[:1] if a.pilot else cases(a.dataset)
        specs={'真实轨迹':None} if a.dataset in TCP else dict(E5.workload_specs(len(setup.h1q)))
        for kib,name,seed,cohort in matrix:
            start=time.perf_counter()
            base=E5.base_stream(setup,name,specs[name],seed,queries=10000000)
            n=len(base)//4;learn,tail=base[:n],base[n:]
            chosen,anchor,bf,info=G.select(setup,scores,safe,learn,kib,len(tail))
            # Old reference and test outcomes are accessed only AFTER selection has finished.
            ref=refs[kib,name,seed]
            assert ah(base)==ref['base_stream_sha256'] and ah(tail)==ref['tail_stream_sha256']
            original=G.ORIGINAL_SUMMARIZE(learn,True)
            assert ah(original.rate)==info['repaired_rate_sha256'],'This matrix was expected to be unaffected by the GT repair'
            ar=tail_result(anchor,tail,setup,safe,a.cache)
            br=tail_result(bf,tail,setup,safe,a.cache)
            for r,key in ((ar,'RA6'),(br,'BF+ReplayCache')):
                for field in ('trees','frac','cache_bytes','total_bytes','model_bytes','fp','hits','static_flags_sha256'):
                    assert r[field]==ref['methods'][key][field],('reference mismatch',a.dataset,kib,name,seed,key,field)
            assert info['zero_learning_fp']==ref['bf_replay_learn_fp']
            # Execute final deployment separately, not just copy the favorable tail count.
            result=tail_result(chosen,tail,setup,safe,a.cache)
            expected=br if info['family']=='zero' else ar
            assert result==expected
            if a.pilot:
                cands=[G.BF.build(setup,kib,f,E5.K) for f in E5.FRACS]+[anchor]
                full=[int(E5.evaluate(c,learn,setup,safe)['fp']) for c in cands]
                assert info['selected_learning_fp']==min(full)
                out['pilot_exhaustive_learning_check']=True
            row=dict(dataset=a.dataset,cache=a.cache,budget_kib=kib,workload=name,seed=seed,cohort=cohort,
                     learn_len=n,tail_len=len(tail),base_stream_sha256=ah(base),tail_stream_sha256=ah(tail),
                     gate=info,methods={'RA6-ZGate':result,'RA6-GT19':ar,'BF+ReplayCache':br},
                     historical_predictive_zero=ref['methods']['RA6-Z'],
                     historical_full_replay=ref['methods']['Replay+Z'],case_wall_s=time.perf_counter()-start)
            out['cases'].append(row);save(a.output,out)
            print(f'CASE {a.dataset}/{kib} {name} s{seed} {a.cache}: family={info["family"]} '
                  f'learn={info["selected_learning_fp"]} BF={info["zero_learning_fp"]} RA={info["anchor_learning_fp"]}; '
                  f'tail={result["fp"]} BF={br["fp"]} RA={ar["fp"]}',flush=True)
        out['status']='ok'
    except Exception:
        out['status']='error';out['error']=traceback.format_exc();print(out['error'],flush=True)
    out.update(python=platform.python_version(),numpy=np.__version__)
    save(a.output,out)
    if out['status']!='ok':raise SystemExit(1)
    print(f'COMPLETE {a.dataset} {a.cache}: {len(out["cases"])} cases',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=DATASETS,required=True);p.add_argument('--cache',choices=('index','fp64'),required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    if a.output.exists():p.error('Output exists; refusing overwrite')
    main(a)

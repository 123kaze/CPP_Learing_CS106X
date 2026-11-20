"""All five selectors rebuilt/timed three times on every case; strict exactness."""
from common_v2 import *
import argparse
import time
import json
import traceback
import resource
import gc
import numpy as np
from selectors_v2 import S,G,E5,measured,grid_choice
from worker21 import warm,compare_exact


def identity(c):
    st=c['structure']
    return dict(trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes'],total_bytes=st.used_bytes,
                static_flags_sha256=ah(st.fp_static))


def expect(cs,learn,setup,safe,keys,counts,mode):
    full,states=S.serial_full(cs,learn,setup,safe,mode)
    joint=S.replay(cs,learn,setup,safe,keys,counts,mode);compare_exact(full,states,joint)
    return dict(counters=full,packed_state_sha256=[ah(s) for s in states],
                candidate_event_visits=joint['visits'].tolist(),additional_route_keys=joint['additional_routed_keys'],
                route_workspace_payload_bytes=joint['route_workspace_payload_bytes'],candidates=len(cs))


def main(a):
    out=dict(status='running',dataset=a.dataset,cache=a.cache,pilot=a.pilot,cases=[])
    try:
        if a.dataset in TCP:
            sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
        E5.K=G.BF.CACHES[a.cache];warm()
        t=time.perf_counter();setup,scores,safe=E5.load(a.dataset)
        for tree in E5.TREES:E5.tree(setup,scores,tree)
        out['common_model_input_prepare_s']=time.perf_counter()-t
        source=WR/f'round20_zero_guard/results/main/{a.dataset}_{a.cache}.json'
        old=json.loads(source.read_text());assert old['status']=='ok'
        refs={(r['budget_kib'],r['workload'],r['seed']):r for r in old['cases']}
        out['round20_sha256']=digest(source)
        matrix=cases(a.dataset)[:1] if a.pilot else cases(a.dataset)
        specs={'真实轨迹':None} if a.dataset in TCP else dict(E5.workload_specs(len(setup.h1q)))
        for ci,(kib,name,seed,cohort) in enumerate(matrix):
            base=E5.base_stream(setup,name,specs[name],seed,10000000)
            learn,tail=base[:len(base)//4],base[len(base)//4:]
            ref=refs[kib,name,seed];assert ah(base)==ref['base_stream_sha256']
            with G.patched():
                lm=G.Z.RA.ra4.summarize(learn,True)
                anchor,_=G.Z.ra6.select6(setup,scores,lm,kib,len(tail))
            assert ah(lm.rate)==ref['gate']['repaired_rate_sha256']
            zeros=[G.BF.build(setup,kib,f,E5.K) for f in E5.FRACS]
            gcands=zeros+[anchor];guard=expect(gcands,learn,setup,safe,lm.keys,lm.counts,a.cache)
            idx,bfi=S.gate_choice(gcands,guard['counters'])
            assert int(guard['counters'][bfi,0])==ref['gate']['zero_learning_fp']
            assert int(guard['counters'][-1,0])==ref['gate']['anchor_learning_fp']
            expected_guard=identity(gcands[idx]);expected_anchor=identity(anchor)
            assert all(expected_guard[k]==ref['methods']['RA6-ZGate'][k] for k in expected_guard)
            assert all(expected_anchor[k]==ref['methods']['RA6-GT19'][k] for k in expected_anchor)
            # Actual tail executions occur only after fixed learning choices.
            guard_fp=int(E5.evaluate(gcands[idx],tail,setup,safe)['fp'])
            anchor_fp=int(E5.evaluate(anchor,tail,setup,safe)['fp'])
            assert guard_fp==ref['methods']['RA6-ZGate']['fp'] and anchor_fp==ref['methods']['RA6-GT19']['fp']
            del gcands,zeros,anchor
            fullcs=E5.candidates(setup,scores,kib)+[G.BF.build(setup,kib,f,E5.K) for f in E5.FRACS]
            grid=expect(fullcs,learn,setup,safe,lm.keys,lm.counts,a.cache)
            gi=grid_choice(fullcs,grid['counters'])
            serial_winner,_=E5.replay_best(fullcs,learn,setup,safe)
            assert serial_winner is fullcs[gi]
            expected_grid=identity(fullcs[gi])
            assert (expected_grid['trees'],expected_grid['frac'])==(ref['historical_full_replay']['trees'],ref['historical_full_replay']['frac'])
            grid_fp=int(E5.evaluate(fullcs[gi],tail,setup,safe)['fp']);assert grid_fp==ref['historical_full_replay']['fp']
            del serial_winner,fullcs,lm
            timings=[]
            for rep in range(REPS):
                shift=(ci+rep+(0 if a.cache=='index' else 1))%len(METHODS)
                order=METHODS[shift:]+METHODS[:shift]
                for method in order:
                    gc.collect()  # outside timing, consistent for every method
                    c,phases,details=measured(method,setup,scores,safe,learn,kib,len(tail),a.cache)
                    target=expected_anchor if method=='RA6' else expected_guard if method.startswith('ZGate') else expected_grid
                    assert identity(c)==target,(method,'selected structure changed')
                    extra={}
                    if details is not None:
                        oracle=guard if method.startswith('ZGate') else grid
                        assert np.array_equal(details['counters'],oracle['counters'])
                        assert [ah(s) for s in details['states']]==oracle['packed_state_sha256']
                        extra=dict(route_workspace_payload_bytes=details['route_workspace_payload_bytes'],
                                   cache_state_bytes=details['cache_state_bytes'],candidate_visits=int(details['visits'].sum()),
                                   all_counters_exact=True,all_cache_bytes_exact=True)
                    timings.append(dict(rep=rep,method=method,**phases,**extra))
                    print(f'TIMED {a.dataset}/{kib} {name} s{seed} {a.cache} rep{rep} {method}: selection={phases["selection_s"]:.6f}s',flush=True)
                    del c,details
            row=dict(dataset=a.dataset,cache=a.cache,budget_kib=kib,workload=name,seed=seed,cohort=cohort,
                     learn_len=len(learn),tail_len=len(tail),base_stream_sha256=ah(base),
                     anchor=expected_anchor,guard=expected_guard,grid=expected_grid,
                     anchor_fp_tail=anchor_fp,guard_fp_tail=guard_fp,grid_fp_tail=grid_fp,
                     guard_verification={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in guard.items()},
                     grid_verification={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in grid.items()},
                     timing=timings)
            assert len(timings)==15
            out['cases'].append(row);save(a.output,out)
            print(f'CASE COMPLETE {a.dataset}/{kib} {name} s{seed} {a.cache}: all5 selectors timed3 times and exact',flush=True)
        out['status']='ok'
    except Exception:
        out['status']='error';out['error']=traceback.format_exc();print(out['error'],flush=True)
    out['whole_process_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    save(a.output,out)
    if out['status']!='ok':raise SystemExit(1)
    print(f'COMPLETE {a.dataset} {a.cache}: {len(out["cases"])} fully timed cases',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=DATASETS,required=True);p.add_argument('--cache',choices=('index','fp64'),required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    if a.output.exists():p.error('Output exists; refusing overwrite')
    main(a)

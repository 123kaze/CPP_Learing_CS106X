"""Exact gate equivalence on round20's matrix; paired replay timings on fixed points."""
from common21 import *
import argparse
import json
import time
import traceback
import resource
import numpy as np
from types import SimpleNamespace
import shared21 as S
G=S.G;E5=S.E5


def warm():
    # Unrelated tiny vectors compile route/serial kernels before measured timings.
    h=np.array([0x1000000000000001,0x3000000000000001,0x7000000000000001],np.uint64)
    setup=SimpleNamespace(h1q=h)
    q=np.array([0,1,2,1,0],np.int64);keys,counts=np.unique(q,return_counts=True)
    cs=[dict(cache_bytes=b,structure=SimpleNamespace(fp_static=np.array([True,False,True]))) for b in (0,256)]
    safe=np.array([4,4,4],np.uint8)
    for mode in ('index','fp64'):
        S.replay(cs,q,setup,safe,keys,counts,mode);S.serial_full(cs,q,setup,safe,mode)


def old_gate(cs,learn,setup,safe):
    start=time.perf_counter()
    bf,fp,_,_=G.replay_bf_family(cs[:13],learn,setup,safe)
    a=int(E5.evaluate(cs[-1],learn,setup,safe)['fp'])
    selected=next(i for i,c in enumerate(cs[:13]) if c is bf) if fp<=a else 13
    return selected,fp,a,time.perf_counter()-start


def compare_exact(full_counts,full_states,joint):
    assert np.array_equal(full_counts,joint['counters']),'Candidate counters changed'
    assert len(full_states)==len(joint['states'])
    for a,b in zip(full_states,joint['states']):assert a.tobytes()==b.tobytes(),'CLOCK packed state changed'


def main(a):
    out=dict(status='running',dataset=a.dataset,cache=a.cache,pilot=a.pilot,cases=[])
    try:
        if a.dataset in TCP:
            sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
        E5.K=G.BF.CACHES[a.cache];warm()
        setup,scores,safe=E5.load(a.dataset)
        source=WR/f'round20_zero_guard/results/main/{a.dataset}_{a.cache}.json'
        old=json.loads(source.read_text());assert old['status']=='ok'
        refs={(r['budget_kib'],r['workload'],r['seed']):r for r in old['cases']}
        out['round20_sha256']=digest(source)
        matrix=cases(a.dataset)[:1] if a.pilot else cases(a.dataset)
        specs={'真实轨迹':None} if a.dataset in TCP else dict(E5.workload_specs(len(setup.h1q)))
        for kib,name,seed,cohort in matrix:
            base=E5.base_stream(setup,name,specs[name],seed,10000000)
            learn,tail=base[:len(base)//4],base[len(base)//4:]
            ref=refs[kib,name,seed]
            assert ah(base)==ref['base_stream_sha256']
            with G.patched():
                begin=time.perf_counter();lm=G.Z.RA.ra4.summarize(learn,True)
                anchor,info=G.Z.ra6.select6(setup,scores,lm,kib,len(tail))
                zeros=[G.BF.build(setup,kib,f,E5.K) for f in E5.FRACS]
                common_build_s=time.perf_counter()-begin
            cs=zeros+[anchor]
            assert ah(lm.rate)==ref['gate']['repaired_rate_sha256']
            old_idx,old_bf,old_anchor,_=old_gate(cs,learn,setup,safe)
            assert (old_bf,old_anchor)==(ref['gate']['zero_learning_fp'],ref['gate']['anchor_learning_fp'])
            full,states=S.serial_full(cs,learn,setup,safe,a.cache)
            joint=S.replay(cs,learn,setup,safe,lm.keys,lm.counts,a.cache)
            compare_exact(full,states,joint)
            idx,bfi=S.gate_choice(cs,joint['counters'])
            assert idx==old_idx and int(full[bfi,0])==old_bf and int(full[13,0])==old_anchor
            selected=cs[idx]
            assert selected['trees']==ref['methods']['RA6-ZGate']['trees']
            assert selected['frac']==ref['methods']['RA6-ZGate']['frac']
            assert ah(selected['structure'].fp_static)==ref['methods']['RA6-ZGate']['static_flags_sha256']
            fp=int(E5.evaluate(selected,tail,setup,safe)['fp'])
            assert fp==ref['methods']['RA6-ZGate']['fp']
            diagnostic=dict(learning_fp_all=full[:,0].tolist(),counters_sha256=ah(full),
                 packed_state_sha256=[ah(x) for x in states],additional_route_keys=joint['additional_routed_keys'],
                 candidate_event_visits=joint['visits'].tolist(),route_workspace_payload_bytes=joint['route_workspace_payload_bytes'],
                 cache_state_bytes=joint['cache_state_bytes'],all_states_bit_exact=True,all_counters_bit_exact=True)
            # Delete heavy verification state before timing; the same candidate inputs remain.
            del joint,states
            timing=[]
            if timed_case(a.dataset,kib,name,seed) and not a.pilot:
                for rep in range(TIMING_REPS):
                    pair={}
                    for method in (('serial','shared') if rep%2==0 else ('shared','serial')):
                        if method=='serial':
                            chosen,bf_fp,ra_fp,seconds=old_gate(cs,learn,setup,safe)
                            assert (chosen,bf_fp,ra_fp)==(old_idx,old_bf,old_anchor)
                            pair[method]=dict(replay_s=seconds)
                        else:
                            result=S.replay(cs,learn,setup,safe,lm.keys,lm.counts,a.cache)
                            assert np.array_equal(result['counters'],full)
                            assert S.gate_choice(cs,result['counters'])[0]==old_idx
                            pair[method]=dict(replay_s=result['elapsed_s'],route_prepare_s=result['route_prepare_s'],
                                               ordered_scan_s=result['ordered_scan_s'])
                            del result
                    timing.append(dict(rep=rep,**pair))
                    print(f'TIMING {a.dataset}/{kib} {a.cache} rep{rep}: serial={pair["serial"]["replay_s"]:.4f}s shared={pair["shared"]["replay_s"]:.4f}s',flush=True)
            row=dict(dataset=a.dataset,cache=a.cache,budget_kib=kib,workload=name,seed=seed,cohort=cohort,
                     learn_len=len(learn),tail_len=len(tail),distinct_keys=len(lm.keys),base_stream_sha256=ah(base),
                     same_round20_choice=True,same_round20_fp=True,chosen_index=idx,bf_winner_index=bfi,
                     chosen_trees=selected['trees'],chosen_frac=selected['frac'],fp_tail=fp,
                     common_summary_anchor_and_bf_build_s=common_build_s,verification=diagnostic,timing=timing)
            out['cases'].append(row);save(a.output,out)
            print(f'CHECKED {a.dataset}/{kib} {name} s{seed} {a.cache}:14 counter/state pairs exact; tail={fp}',flush=True)
            del cs,zeros,anchor,full
        out['status']='ok'
    except Exception:
        out['status']='error';out['error']=traceback.format_exc();print(out['error'],flush=True)
    out['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    save(a.output,out)
    if out['status']!='ok':raise SystemExit(1)
    print(f'COMPLETE {a.dataset} {a.cache}: {len(out["cases"])} exact cases',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=DATASETS,required=True);p.add_argument('--cache',choices=('index','fp64'),required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    if a.output.exists():p.error('Output exists; refusing overwrite')
    main(a)

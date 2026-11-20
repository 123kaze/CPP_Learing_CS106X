"""Apply the same shared replay optimization to full learned+zero grid fairly.

Prespecified URL128/CAIDA256 Zipf/full seed0, both cache formats. This is a
selection-replay microbenchmark, not a repeated full model-training campaign.
"""
from common21 import *
import argparse
import time
import json
import traceback
import numpy as np
import shared21 as S
from worker21 import warm,compare_exact
G=S.G;E5=S.E5


def main(ds,mode,outfile):
    out=dict(status='running',dataset=ds,cache=mode)
    try:
        E5.K=G.BF.CACHES[mode];warm()
        kib=MID[ds];setup,scores,safe=E5.load(ds)
        base=E5.base_stream(setup,'zipf1.0-全部',('zipf',None,1.0),0,10000000)
        learn=base[:len(base)//4]
        start=time.perf_counter();keys,counts=np.unique(learn,return_counts=True);summary_s=time.perf_counter()-start
        start=time.perf_counter();cs=E5.candidates(setup,scores,kib)+[G.BF.build(setup,kib,f,E5.K) for f in E5.FRACS]
        build_s=time.perf_counter()-start
        full,states=S.serial_full(cs,learn,setup,safe,mode)
        joint=S.replay(cs,learn,setup,safe,keys,counts,mode);compare_exact(full,states,joint)
        best=min(range(len(cs)),key=lambda i:(int(full[i,0]),cs[i]['structure'].est_fpr,cs[i]['trees'],cs[i]['frac']))
        original,fp=E5.replay_best(cs,learn,setup,safe)
        assert original is cs[best]
        prior=json.loads((WR/f'round20_zero_guard/results/main/{ds}_{mode}.json').read_text())
        ref=next(r for r in prior['cases'] if r['budget_kib']==kib and r['workload']=='zipf1.0-全部' and r['seed']==0)
        assert ah(base)==ref['base_stream_sha256']
        assert (original['trees'],original['frac'])==(ref['historical_full_replay']['trees'],ref['historical_full_replay']['frac'])
        out.update(all_counter_pairs_exact=True,all_packed_state_pairs_exact=True,candidates=len(cs),learning_fp=int(full[best,0]),
                   trees=original['trees'],frac=original['frac'],common_count_s=summary_s,common_build_s=build_s,
                   candidate_visits=int(joint['visits'].sum()),additional_route_keys=joint['additional_routed_keys'],
                   route_workspace_payload_bytes=joint['route_workspace_payload_bytes'],base_stream_sha256=ah(base),learn_len=len(learn),timing=[])
        del states,joint
        for rep in range(TIMING_REPS):
            pair={}
            for method in (('serial','shared') if rep%2==0 else ('shared','serial')):
                if method=='serial':
                    t=time.perf_counter();chosen,_=E5.replay_best(cs,learn,setup,safe);elapsed=time.perf_counter()-t
                    assert chosen is cs[best];pair[method]=dict(replay_s=elapsed)
                else:
                    r=S.replay(cs,learn,setup,safe,keys,counts,mode)
                    assert np.array_equal(r['counters'],full)
                    pair[method]=dict(replay_s=r['elapsed_s'],route_prepare_s=r['route_prepare_s'],ordered_scan_s=r['ordered_scan_s']);del r
            out['timing'].append(dict(rep=rep,**pair))
            print(f'GRID TIMING {ds} {mode} rep{rep}: serial={pair["serial"]["replay_s"]:.4f} shared={pair["shared"]["replay_s"]:.4f}',flush=True)
        out['status']='ok'
    except Exception:
        out['status']='error';out['error']=traceback.format_exc();print(out['error'],flush=True)
    save(outfile,out)
    if out['status']!='ok':raise SystemExit(1)
    print(f'COMPLETE full-grid {ds} {mode}',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=('url','caida'),required=True);p.add_argument('--cache',choices=('index','fp64'),required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Output exists; refusing overwrite')
    main(a.dataset,a.cache,a.output)

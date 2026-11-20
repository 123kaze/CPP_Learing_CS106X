"""Fresh candidate construction inside EVERY selection timer; cached models outside."""
import time
import numpy as np
from common_v2 import *
import shared21 as S
G=S.G;E5=S.E5


def grid_choice(cs,counts):
    return min(range(len(cs)),key=lambda i:(int(counts[i,0]),cs[i]['structure'].est_fpr,cs[i]['trees'],cs[i]['frac']))


def measured(method,setup,scores,safe,learn,kib,H,mode):
    if method=='ZGate-serial':
        c,anchor,bf,info=G.select(setup,scores,safe,learn,kib,H)
        phases=dict(statistics_s=info['summary_s'],anchor_select_build_s=info['anchor_select_build_s'],
                    candidate_build_s=info['zero_candidates_build_s'],route_s=0.,
                    replay_s=info['zero_replay_s']+info['anchor_replay_s'],selection_s=info['selection_s'])
        return c,phases,None
    if method=='RA6' or method=='ZGate-shared':
        with G.patched():
            begin=time.perf_counter();lm=G.Z.RA.ra4.summarize(learn,True);count_end=time.perf_counter()
            anchor,_=G.Z.ra6.select6(setup,scores,lm,kib,H);anchor_end=time.perf_counter()
            if method=='RA6':
                phases=dict(statistics_s=count_end-begin,anchor_select_build_s=anchor_end-count_end,
                            candidate_build_s=0.,route_s=0.,replay_s=0.,selection_s=anchor_end-begin)
                return anchor,phases,None
            zeros=[G.BF.build(setup,kib,f,E5.K) for f in E5.FRACS];build_end=time.perf_counter()
            cs=zeros+[anchor]
            result=S.replay(cs,learn,setup,safe,lm.keys,lm.counts,mode)
            i,_=S.gate_choice(cs,result['counters']);end=time.perf_counter()
            phases=dict(statistics_s=count_end-begin,anchor_select_build_s=anchor_end-count_end,
                        candidate_build_s=build_end-anchor_end,route_s=result['route_prepare_s'],
                        replay_s=result['ordered_scan_s'],selection_s=end-begin)
            return cs[i],phases,result
    begin=time.perf_counter()
    keys=counts=None
    if method=='Grid-shared':keys,counts=np.unique(learn,return_counts=True)
    count_end=time.perf_counter()
    cs=E5.candidates(setup,scores,kib)+[G.BF.build(setup,kib,f,E5.K) for f in E5.FRACS]
    build_end=time.perf_counter()
    if method=='Grid-serial':
        c,_=E5.replay_best(cs,learn,setup,safe);end=time.perf_counter()
        phases=dict(statistics_s=0.,anchor_select_build_s=0.,candidate_build_s=build_end-begin,
                    route_s=0.,replay_s=end-build_end,selection_s=end-begin)
        # The frozen replay timer includes its bincount preprocessing.
        return c,phases,None
    if method!='Grid-shared':raise ValueError(method)
    result=S.replay(cs,learn,setup,safe,keys,counts,mode)
    i=grid_choice(cs,result['counters']);end=time.perf_counter()
    phases=dict(statistics_s=count_end-begin,anchor_select_build_s=0.,candidate_build_s=build_end-count_end,
                route_s=result['route_prepare_s'],replay_s=result['ordered_scan_s'],selection_s=end-begin)
    return cs[i],phases,result

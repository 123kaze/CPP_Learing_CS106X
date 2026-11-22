"""New fixed-region controls; no edits to the frozen RA6 selector."""
import os
for _v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round27_http_real/src'))
import worker27 as W
sys.path.insert(0,str(WR/'round28_reweight_mechanism/src'))
import mechanism28 as M
import hashlib
import json
import time
import numpy as np
E5=W.E5;RA=W.ra5
SEEDS=(3601,3602,3603)


def budgets(n):
    return tuple(max(4,(int(n)*b+8191)//8192) for b in (2,4,8))


def check_freeze():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['sources'].items():assert W.sha(BLOOM/p)==h,p
    for p,h in f['inputs'].items():assert W.sha(BLOOM/p)==h,p
    return W.sha(ROOT/'plan/freeze.json')


def region_masses(P,td,reg_seg,eps_h,slots):
    k=len(eps_h)
    out={'h':np.bincount(reg_seg,weights=td.h,minlength=k)}
    for name,s in (('traffic',0),('miss',slots)):
        raw=P.misses(eps_h[reg_seg],s,True)
        floor=RA.FLOOR*max(float(raw.sum()),1e-300)*td.h
        out[name]=np.bincount(reg_seg,weights=raw+floor,minlength=k)
    return out


def controls(setup,scores,lm,H,kib,tail,safe):
    start=time.perf_counter()
    anchors=E5.candidates(setup,scores,kib,fracs=(.1,))
    if not anchors:
        return dict(status='infeasible',budget_kib=kib,reason='No validation anchor at fixed 10% cache',rows=[],wall_s=time.perf_counter()-start)
    anchor=min(anchors,key=lambda c:(c['structure'].est_fpr,c['trees']))
    st=anchor['structure'];td=E5.tree(setup,scores,anchor['trees'])
    reg=E5.D.region_of_segment(st.b)
    member_region=reg[td.seg_m].astype(np.int32);negative_region=reg[td.seg_q].astype(np.int32)
    n=np.bincount(member_region,minlength=len(st.f)).astype(float)
    h=np.bincount(reg,weights=td.h,minlength=len(st.f))
    bits=int((kib*1024-td.fixed-anchor['cache_bytes'])*8)
    assert bits>0 and bits%8==0
    eps_h=M.capped(n,h,bits)
    population=RA.population(lm,td,H,RA.Config(new_mix=0.))
    mass=region_masses(population,td,reg,eps_h,anchor['slots'])
    assert np.array_equal(mass['h'],h)
    identity=M.identity(n,h,mass['miss'],bits)
    shared_s=time.perf_counter()-start
    rows=[]
    for arm in ('h','traffic','miss'):
        t=time.perf_counter();eps=M.capped(n,mass[arm],bits)
        flags,physical=M.physical(n,eps,setup.h1m,setup.h1q,member_region,negative_region,bits)
        build_s=time.perf_counter()-t
        assert physical['navigation_payload_bytes']+st.b.nbytes<=td.metadata_bytes
        used=int(td.fixed+anchor['cache_bytes']+physical['payload_bytes'])
        assert used<=kib*1024
        t=time.perf_counter()
        result,actual_cache=M.clock(tail,setup.h1q,safe,flags,setup.h1m,anchor['cache_bytes'])
        replay_s=time.perf_counter()-t
        assert actual_cache==anchor['cache_bytes']
        rows.append(dict(arm=arm,**result,member_fn=0,weights=mass[arm].tolist(),continuous_epsilon=eps.tolist(),
                         physical=physical,total_bytes=used,model_payload_bytes=int(td.model_bytes),
                         metadata_reserved_bytes=int(td.metadata_bytes),array_header_reserved_bytes=int(td.overhead_bytes),
                         cache_physical_bytes=actual_cache,static_flags_sha256=W.ah(flags),build_s=build_s,tail_replay_s=replay_s))
    return dict(status='complete',budget_kib=kib,trees=anchor['trees'],cache_frac=.1,cache_bytes=anchor['cache_bytes'],slots=anchor['slots'],
                bf_budget_bits=bits,partition=st.b.tolist(),partition_sha256=W.ah(st.b),
                model_array_hashes={k:W.ah(v) for k,v in E5.R._MODEL_ARRAYS[setup.name,anchor['trees']].items()},
                member_region_counts=n.astype(int).tolist(),h=h.tolist(),shared_prepare_s=shared_s,
                conditional_identity=identity,actual_clock_fixed_T_condition=False,rows=rows,wall_s=time.perf_counter()-start)

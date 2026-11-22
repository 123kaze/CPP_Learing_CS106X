"""Horizon-only wrappers around frozen RA6; no tail argument in selector API."""
import os
for _v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round27_http_real/src'))
import worker27 as W
sys.path.insert(0,str(WR/'round32_no_repeat_guard/src'))
from worker32 import payload
import cache_fp
import numpy as np
from contextlib import contextmanager
import hashlib,json,time
E5=W.E5;RA=W.ra5;R6=W.ra6
CACHES={'index':E5.K,'fp64':cache_fp}
RULES=('quarter','matched','fourfold','three_learning')
ORIGINAL_TABLE=RA.candidate_table
ORIGINAL_BUCKET=R6.bucket_prediction


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def cases():
    rows=[]
    for ds,kib in (('cod',1024),('url',128),('caida',256),('shalla',1024)):
        rows.append(dict(dataset=ds,budget_kib=kib,seed=0,workload='zipf1.0-全部',cohort='paper_zipf'))
    for ds in ('caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow'):
        rows.append(dict(dataset=ds,budget_kib=24,seed=0,workload='真实轨迹',cohort='real_trace'))
    for ds,kib in (('caida_tcp_flow',32),('mawi2020_tcp_flow',64),('mawi2021_tcp_flow',41),('mawi2022_tcp_flow',64)):
        rows.append(dict(dataset=ds,budget_kib=kib,seed=0,workload='真实轨迹',cohort='tcp_only'))
    for seed in (3601,3602,3603):
        for kib in (8,16,32):rows.append(dict(dataset='clarknet',budget_kib=kib,seed=seed,workload='natural_404',cohort='http'))
    assert len(rows)==21
    return rows


def horizons(L,actual):
    if not isinstance(L,int) or not isinstance(actual,int) or min(L,actual)<=0:
        raise ValueError('Positive integer learning and actual query counts required')
    return dict(quarter=max(1,actual//4),matched=actual,fourfold=4*actual,three_learning=3*L)


def rule_order(index):
    n=index%len(RULES)
    return RULES[n:]+RULES[:n]


def check_freeze():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['sources'].items():assert sha(BLOOM/p)==h,p
    return sha(ROOT/'plan/freeze.json')


@contextmanager
def observe(H):
    assert RA.candidate_table is ORIGINAL_TABLE and R6.bucket_prediction is ORIGINAL_BUCKET, 'Leaked or nested wrapper'
    captured={'stage1_H':[],'stage2_H':[]}
    def table(setup,scores,lm,kib,h,*args,**kwargs):
        assert h==H;captured['stage1_H'].append(int(h))
        result=ORIGINAL_TABLE(setup,scores,lm,kib,h,*args,**kwargs)
        captured['table']=result
        return result
    def bucket(setup,lm,td,c,h,seg_fpr):
        assert h==H;captured['stage2_H'].append(int(h))
        return ORIGINAL_BUCKET(setup,lm,td,c,h,seg_fpr)
    RA.candidate_table=table;R6.bucket_prediction=bucket
    try:yield captured
    finally:RA.candidate_table=ORIGINAL_TABLE;R6.bucket_prediction=ORIGINAL_BUCKET


def select(setup,scores,lm,kib,assumed_H):
    if not isinstance(assumed_H,int) or assumed_H<=0:raise ValueError('Positive integer H required')
    with observe(assumed_H) as cap:
        start=time.perf_counter();c,info=R6.select6(setup,scores,lm,kib,assumed_H);elapsed=time.perf_counter()-start
    assert cap['stage1_H']==[assumed_H] and len(cap['stage2_H'])==info['built']
    start=time.perf_counter()
    ordered=sorted(cap['table'],key=lambda r:(r['pred'],r['trees'],r['frac']))
    table=[dict(rank=i,trees=r['trees'],frac=r['frac'],cache_bytes=r['cache_bytes'],slots=r['slots'],predicted_fp=r['pred'],
                weights_sha256=W.ah(r['weights']),seg_fpr_sha256=W.ah(r['seg_fpr_pred'])) for i,r in enumerate(ordered)]
    return c,dict(**info,select_build_wall_s=elapsed,candidate_diagnostic_s=time.perf_counter()-start,
                  stage1_H=cap['stage1_H'],stage2_H=cap['stage2_H'],table=table)


def arrays_equal(a,b):
    return a.keys()==b.keys() and all(a[k].dtype==b[k].dtype and a[k].shape==b[k].shape and
                                     np.array_equal(a[k].view(np.uint8),b[k].view(np.uint8)) for k in a)


def evaluate(c,stream,s,safe,mode):
    cache=CACHES[mode];spec=cache.layout(c['cache_bytes']);data=cache.allocate(spec)
    aux=safe if mode=='index' else np.empty(0,np.bool_)
    start=time.perf_counter()
    count=cache.replay(stream,s.h1q,aux,c['structure'].fp_static,data,spec['buckets'],spec['prefix_bits'],spec['Q'],spec['ob'],spec['slot_bits'],4,spec['handbits'],2**62,np.empty(0,np.int64),np.empty(0,np.bool_))
    replay_s=time.perf_counter()-start
    assert count[5]==len(stream) and count[6]==0
    start=time.perf_counter()
    fn=int(cache.count_member_hits(data,s.h1m,spec['buckets'],spec['prefix_bits'],spec['Q'],spec['ob'],spec['slot_bits'],4))
    check_s=time.perf_counter()-start
    if mode=='index':assert fn==0
    result=dict(zip(('fp','hits','inserts','evictions','bypasses','processed','cutoff','occupied'),map(int,count[:8])))
    result.update(member_cache_hits_final=fn,cache_state_sha256=W.ah(data),tail_replay_s=replay_s,
                  member_cache_check_s=check_s,fp64_ideal_hash_bound_per_query=min(1.,spec['slots']/2**64) if mode=='fp64' else None)
    return result,data

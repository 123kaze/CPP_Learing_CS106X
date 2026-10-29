import json,numpy as np
from types import SimpleNamespace
import engine as E
rng=np.random.default_rng(5304)
mem=np.sort(rng.integers(0,2**64,2000,dtype=np.uint64));h=rng.integers(0,2**64,1000,dtype=np.uint64)
safe=E.CC.safe_prefix_lengths(mem,h);fp=rng.random(len(h))<.08
setup=SimpleNamespace(h1q=h);stream=rng.integers(0,len(h),200000,dtype=np.int64)
checks=[]
for policy in ('clock','bucket_lru','fifo'):
    for admit in (1,2):
        cache=E.allocated(65536,policy,admit=admit)
        c=dict(structure=SimpleNamespace(fp_static=fp),cache_bytes=cache,prefix_bits=40,policy=policy,ways=4,admit=admit)
        full=E.simulate(c,stream,setup,safe,collect=True);fast=E.evaluate(c,stream,setup,safe)
        assert (full['fp'],full['distinct_fp_keys'])==(fast['fp'],fast['distinct_fp_keys'])
        assert full['evictions']==0
        checks.append(f'{policy}/admit{admit}: no-eviction event replay equals full query replay')
cands=[]
for i,t in enumerate((8,16,48,64)):
    mask=rng.random(len(h))<(.1+i*.03)
    cands.append(dict(trees=t,frac=.1,structure=SimpleNamespace(fp_static=mask,est_fpr=float(mask.mean())),cache_bytes=E.allocated(4096),prefix_bits=40,policy='clock',ways=4,admit=1))
brute=[(E.simulate(c,stream,setup,safe)['fp'],c['structure'].est_fpr,c['trees'],c['frac'],c) for c in cands]
best,fixed,_,_=E.exact_grid(cands,stream,setup,safe)
assert (best['trees'],best['frac'])==(min(brute,key=lambda x:x[:4])[-1]['trees'],.1)
assert fixed['trees']==48
checks.append('multi-objective early-stop grid matches full brute-force best and fixed48 best')
duplicates=[]
for c in cands:
    for f in (.002,.001,.005):duplicates.append(dict(c,frac=f))
brute=[(E.simulate(c,stream,setup,safe)['fp'],c['structure'].est_fpr,c['trees'],c['frac'],c) for c in duplicates]
best,fixed,_,records=E.exact_grid(duplicates,stream,setup,safe)
assert (best['trees'],best['frac'])==tuple(min(brute,key=lambda x:x[:4])[2:4])
assert sum(r['identical_layout_reused'] for r in records)==8
checks.append('identical physical layouts reuse exact counts or monotone lower bounds without changing optimum or tie breaks')
out=dict(status='passed',checks=checks)
E.save(E.ROOT/'evidence'/'exact-replay-tests.json',out);print(json.dumps(out),flush=True)

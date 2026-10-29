"""Measured global LRU/FIFO layouts, with exact FP-event skipping."""
import numpy as np
from numba import njit
import engine as E
import global_lru as G
@njit(cache=True)
def fifo(events,hashes,safe,data,capacity,table_slots):
    result=np.zeros(4,np.int64)
    for x in events:
        h=hashes[x]
        _,found=G._find(data,h,capacity,table_slots) if capacity else (0,0)
        if found:result[1]+=1
        else:
            result[0]+=1
            status=G.cache_insert(data,h,safe[x],capacity,table_slots)
            result[2]+=status==1;result[3]+=status==2
    return result
def run(policy,stream,setup,safe,fp,budget):
    spec=G.layout(budget)
    # Full hashes of observed keys are unique. Thus a raw-filter rejection cannot
    # hit this exact-key cache, nor change its state, unlike a prefix cache.
    events=stream[fp[stream]]
    if policy=='global_lru':
        result=G.simulate(events,setup.h1q,safe,fp,budget)
        return dict(fp=result['fp_full'],cache_allocated_bytes=result['allocated_bytes'],
                    occupied=result['occupied'],capacity=result['capacity'],evictions=result['evictions'])
    data=G.allocate(spec)
    r=fifo(events,setup.h1q,safe,data,spec['capacity'],spec['table_slots'])
    return dict(fp=int(r[0]),cache_allocated_bytes=spec['allocated_bytes'],occupied=int(r[2]),
                capacity=spec['capacity'],evictions=int(r[3]))

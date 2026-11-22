"""Client filter receives only a backend-certified prefix, not a membership index or labels."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(WR/'round31_sqlite_online/src'))
from rpc35 import Client,ProtocolError
from online31 import np,K,njit


@njit(cache=True)
def admit_from_prefix(data,h,length,nb,Q,ob,sb,hb):
    if not nb:return 0
    return K.insert(data,h,length,nb,40,Q,ob,sb,4,hb)


class RpcFilter:
    def __init__(self,prepared):
        # Deliberately do not retain prepared, space, sorted_members or feedback_args.
        self.c=prepared.c;self.hashes=prepared.hashes;self.spec=prepared.spec;self.is_learned=prepared.is_learned
        self.impl=prepared.impl;self.base_args=prepared.base_args;self.reset()

    def reset(self):
        self.data=np.zeros(1,np.uint64) if self.is_learned and not self.spec['buckets'] else K.allocate(self.spec)
        p=self.spec;self.args=(*self.base_args,self.data,p['buckets'],p['Q'],p['ob'],p['slot_bits'])

    def probe(self,x):return self.impl(x,*self.args)

    def confirmed_absent(self,x,length):
        p=self.spec
        if not p['buckets']:return 0
        if not 1<=length<=65:raise ProtocolError('Missing backend safety certificate')
        return admit_from_prefix(self.data,self.hashes[x],length,p['buckets'],p['Q'],p['ob'],p['slot_bits'],p['handbits'])


def online_rpc(rpc,keys,requests,flt,accepted):
    """One outstanding request; actual TCP reply drives every negative-cache insertion."""
    calls=misses=found=hits=rejects=inserts=evictions=bypasses=value_bytes=0
    probe=flt.probe if flt is not None else None
    absent=flt.confirmed_absent if flt is not None else None
    need_prefix=bool(flt is not None and flt.spec['buckets'])
    cpu0=time.process_time_ns();t0=time.perf_counter_ns()
    for i,index in enumerate(requests):
        x=int(index);decision=probe(x) if probe is not None else 1
        if decision==2:hits+=1;continue
        if decision==0:rejects+=1;continue
        accepted[i]=1;calls+=1
        present,length,nb=rpc.get(int(keys[x]),need_prefix)
        if present:found+=1;value_bytes+=nb
        else:
            misses+=1
            if absent is not None:
                outcome=absent(x,length)
                if outcome:inserts+=1;evictions+=int(outcome==2)
                else:bypasses+=1
    elapsed=time.perf_counter_ns()-t0;cpu=time.process_time_ns()-cpu0
    return dict(elapsed_ns=elapsed,ns_per_query=elapsed/len(requests),client_cpu_ns=cpu,backend_calls=calls,fp=misses,members_found=found,
                cache_hits=hits,filter_rejects=rejects,inserts=inserts,evictions=evictions,bypasses=bypasses,received_value_bytes=value_bytes,
                need_backend_prefix=need_prefix,query_sent_bytes=rpc.query_sent_bytes,query_received_bytes=rpc.query_received_bytes)

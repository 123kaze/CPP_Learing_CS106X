"""Independent regression, prefix safety, early-stop and layout tests."""
from pathlib import Path
import sys,json,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'src'))
import compact_cache as old
import fast_cache as F
import numpy as np
def main():
    rng=np.random.default_rng(20261028)
    mem=np.sort(rng.integers(0,2**64,2000,dtype=np.uint64))
    hashes=rng.integers(0,2**64,10000,dtype=np.uint64)
    safe=old.safe_prefix_lengths(mem,hashes)
    fp=rng.random(len(hashes))<.35
    stream=rng.integers(0,len(hashes),100000,dtype=np.int64)
    checks=[]
    for policy,old_policy in [('clock','clock'),('bucket_lru','lru')]:
        for budget in (4096,16384,65536):
            result=F.simulate(stream,hashes,safe,fp,budget,policy)
            ref=old.simulate(stream,hashes,safe,fp,budget,policy=old_policy)
            assert result['fp']==ref['fp_full'],(policy,budget,result,ref)
            assert result['allocated_bytes']<=budget
            short=F.simulate(stream,hashes,safe,fp,budget,policy,limit=result['fp']//3)
            assert short['cutoff'] and short['fp']==result['fp']//3+1 and short['processed']<len(stream)
            checks.append(f'{policy}/{budget}: byte-packed reference and monotone stopping agree')
    for prefix in (24,32,40,56,64):
        for ways in (2,4,8):
            spec=F.layout(8192,prefix,'clock',ways);slab=F.allocate(spec)
            for h,length in zip(hashes,safe):
                if not F.lookup(slab,h,spec['qbits'],spec['rbits'],spec['slot_bits'],ways,0):
                    F.insert(slab,h,length,spec['qbits'],spec['rbits'],spec['slot_bits'],ways,0,spec['handbits'])
            assert all(not F.lookup(slab,h,spec['qbits'],spec['rbits'],spec['slot_bits'],ways,0) for h in mem)
    checks.append('all 15 prefix/ways layouts reject no member after saturation')
    start=time.perf_counter();sample=F.simulate(stream,hashes,safe,fp,16384)
    elapsed=time.perf_counter()-start
    out=dict(status='passed',checks=checks,queries=len(stream),seconds=elapsed,query_ns=elapsed*1e9/len(stream),fp=sample['fp'])
    (ROOT/'evidence'/'fast-cache-tests.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(out),flush=True)
if __name__=='__main__':main()

"""Create a real immutable member database and fixed requests, not timed query results."""
from common16 import *
import time
import numpy as np
from native16 import E5,C
import rocksdict as R


def main():
    done=ROOT/'results/database.json'
    if done.exists():
        r=json.loads(done.read_text());assert r['status']=='complete'
        for rel,h in r['sst_sha256'].items():assert digest(ROOT/rel)==h
        print('DATABASE ALREADY PREPARED',flush=True);return
    path=ROOT/'db/url'
    assert not path.exists(),'Partial database exists; no automatic overwrite'
    ids,y,X,features=C.load_dataset(DS);sp=C.make_split(ids,y,DS)
    all_ids=np.concatenate([ids[y],ids[sp['neg_test']]])
    all_X=np.ascontiguousarray(np.vstack([X[y],X[sp['neg_test']]]))
    nm=int(y.sum());nq=int(sp['neg_test'].sum())
    assert nq>=LEARN+TAIL and len(np.unique(all_ids))==len(all_ids)
    np.savez(ROOT/'inputs/requests.npz',ids=all_ids,X=all_X,members=np.array(nm))
    for w in WORKLOADS:
        rng=np.random.default_rng(16001)
        if w=='once':neg=rng.permutation(nq)[:LEARN+TAIL]
        else:
            cdf=np.cumsum(1/np.arange(1,nq+1));cdf/=cdf[-1]
            perm=rng.permutation(nq);neg=perm[np.searchsorted(cdf,rng.random(LEARN+TAIL))]
        learn=neg[:LEARN].astype(np.int64);tail=neg[LEARN:].astype(np.int64)
        rng=np.random.default_rng(16002)
        mixed=np.concatenate([tail+nm,rng.integers(0,nm,POS,dtype=np.int64)])
        rng.shuffle(mixed)
        np.save(ROOT/f'inputs/{w}_learn.npy',learn);np.save(ROOT/f'inputs/{w}_tail.npy',mixed)
    opts,cache=db_options(CACHES['fit'],True)
    db=R.Rdict(str(path),opts);start=time.perf_counter();rng=np.random.default_rng(16003)
    for lo in range(0,nm,256):
        batch=R.WriteBatch(raw_mode=True)
        payloads=rng.integers(0,256,size=(min(256,nm-lo),VALUE_BYTES-8),dtype=np.uint8)
        for j,p in enumerate(payloads):
            key=key_bytes(all_ids[lo+j]);batch.put(key,key+p.tobytes())
        db.write(batch)
    db.flush();db.compact_range(None,None)
    files=db.live_files();size=db.property_int_value('rocksdb.total-sst-files-size')
    assert sum(f['num_entries'] for f in files)==nm
    for i in range(0,nm,997):assert db.get(key_bytes(all_ids[i]))[:8]==key_bytes(all_ids[i])
    db.close()
    sst={str(p.relative_to(ROOT)):digest(p) for p in path.glob('*.sst')}
    inputs={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'inputs').glob('*')}
    save(done,dict(status='complete',dataset=DS,members=nm,negative_pool=nq,value_bytes=VALUE_BYTES,
                   sst_bytes=size,sst_sha256=sst,inputs_sha256=inputs,creation_s=time.perf_counter()-start,
                   internal_bloom_bits_per_key=10,compression='RocksDB default (not disabled)',
                   data_origin='Frozen URL membership/features; synthetic point-query sequence and random values',
                   files=[{k:v for k,v in f.items() if k not in ('start_key','end_key')} for f in files]))
    print(f'DATABASE COMPLETE: {nm} keys, {size/2**20:.1f}MiB SST, internal Bloom enabled',flush=True)


if __name__=='__main__':main()

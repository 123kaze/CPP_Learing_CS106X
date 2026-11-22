"""Recover exact raw keys locally, verify existing static catalogue; never publish raw bytes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from exact41 import ROOT,WR,BLOOM,W,np,pack
import json,gzip,hashlib,time
sys.path.insert(0,str(WR/'round36_http_qualification/src'))
import data36
INPUT=WR/'round36_http_qualification/cache/clarknet.npz'
SOURCES=(WR/'round36_http_qualification/inputs/clarknet_aug28/assembled/clarknet_access_log_Aug28.gz',WR/'round36_http_qualification/inputs/clarknet_sep4/assembled/clarknet_access_log_Sep4.gz')
OUTPUT=ROOT/'cache/raw_keys.npz'


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for rel,sha in f.get(section,{}).items():assert W.sha(BLOOM/rel)==sha,rel
    return W.sha(ROOT/'plan/freeze.json')


def extract():
    check();assert not OUTPUT.exists();start=time.perf_counter()
    with np.load(INPUT,allow_pickle=False) as d:ids,y,X,trace,order=[d[k] for k in ('ids','y','X','trace','order')]
    by={int(v):i for i,v in enumerate(ids)};keys=[None]*len(ids);count=parsed=0
    # Full replay of stable records verifies order, key identity and status. Client identity discarded.
    for source in SOURCES:
        with gzip.open(source,'rb') as f:
            while True:
                line=f.readline(65537)
                if not line:break
                assert len(line)<=65536
                item,_=data36.decode_line(line)
                if item is None:continue
                _,key,status,_=item;ordinal=parsed;parsed+=1
                if status not in (200,304,404):continue
                ident=int.from_bytes(hashlib.sha256(key).digest()[:8],'little');i=by.get(ident)
                if i is None:continue
                assert count<len(trace) and i==int(trace[count]) and ordinal==int(order[count])
                assert bool(y[i])==(status!=404)
                if keys[i] is None:keys[i]=key
                else:assert keys[i]==key,'Compressed identity alias; refuse raw-key mismatch'
                count+=1
    assert count==len(trace) and all(k is not None for k in keys)
    assert np.array_equal(np.asarray([data36.lexical(k) for k in keys],np.float32),X)
    blob,offsets=pack(keys);OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    np.savez(OUTPUT,blob=blob,offsets=offsets)
    out=dict(status='complete',keys=len(keys),members=int(y.sum()),matched_records=count,raw_key_payload_bytes=len(blob),keys_longer_than128=int(np.sum(np.diff(offsets)>128)),seconds=time.perf_counter()-start,sha256=W.sha(OUTPUT),source_sha256={str(p.relative_to(BLOOM)):W.sha(p) for p in SOURCES})
    W.save(ROOT/'results/raw_key_verification.json',out);check();print('RAW_KEYS_VERIFIED',count,'records',out['seconds'],'seconds',flush=True)


if __name__=='__main__':extract()

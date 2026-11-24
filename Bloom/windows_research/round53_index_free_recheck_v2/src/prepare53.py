"""Recover complete keys from existing original CSVs; publish hashes and counts, never key contents."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
import pandas as pd
import resource


def pack(keys):
    lengths=np.fromiter((len(k) for k in keys),np.int64,count=len(keys))
    offsets=np.concatenate((np.zeros(1,np.int64),np.cumsum(lengths)))
    return np.frombuffer(b''.join(keys),np.uint8).copy(),offsets


def encode_address(text,nbytes):
    value=int(text)
    assert str(value)==text and 0<=value<2**(8*nbytes),'Noncanonical/out-of-range address'
    return value.to_bytes(nbytes,'little')


def prepare(ds):
    start=time.perf_counter();check_inputs(ds)
    out=ROOT/f'cache/{ds}.npz';assert not out.exists()
    with np.load(C.CACHE/ds/'data.npz',allow_pickle=False) as f:ids,y=f['ids'],f['y']
    assert len(np.unique(ids))==len(ids)
    paths=raw_paths(ds);raw_rows=0
    if ds in ('cod','caida'):
        key,label=('objID','type') if ds=='cod' else ('No.','Label')
        cursor=0
        for path in paths:
            for chunk in pd.read_csv(path,usecols=[key,label],chunksize=200000):
                values=chunk[key].to_numpy()
                assert values.dtype.kind in 'iu' and np.all(values>=0)
                values=values.astype(np.uint64)
                yy=(chunk[label].to_numpy()==('galaxy' if ds=='cod' else 1))
                assert np.array_equal(values,ids[cursor:cursor+len(chunk)])
                assert np.array_equal(yy,y[cursor:cursor+len(chunk)])
                cursor+=len(chunk)
        assert cursor==len(ids);raw_rows=cursor
        blob=ids.astype('<u8').view(np.uint8).copy();offsets=np.arange(len(ids)+1,dtype=np.int64)*8
    elif ds.endswith('_flow'):
        order=np.argsort(ids);sorted_ids=ids[order]
        w=width(ds);address_bytes=(w-1)//2
        keys=np.zeros((len(ids),w),np.uint8);seen=np.zeros(len(ids),np.bool_)
        first_cursor=0
        for chunk in pd.read_csv(paths[0],usecols=['Source','Destination','Label'],dtype={'Source':str,'Destination':str},chunksize=200000):
            raw_rows+=len(chunk)
            # Drop only equal original tuples, never equality of compressed hash IDs.
            chunk=chunk.drop_duplicates(['Source','Destination','Label'])
            a,b,lab=(chunk[k].to_numpy() for k in ('Source','Destination','Label'))
            assert lab.dtype.kind in 'iu' and np.isin(lab,[0,1]).all()
            text=chunk.Source+'>'+chunk.Destination+'#'+chunk.Label.astype(str)
            hid=pd.util.hash_pandas_object(text,index=False).to_numpy(np.uint64)
            assert len(np.unique(hid))==len(hid),'Distinct original tuple hash alias within chunk'
            pos=np.searchsorted(sorted_ids,hid);assert np.all(pos<len(ids))
            assert np.array_equal(sorted_ids[pos],hid);ix=order[pos]
            encoded=np.empty((len(chunk),w),np.uint8)
            encoded[:,:address_bytes]=np.frombuffer(b''.join(encode_address(v,address_bytes) for v in a),np.uint8).reshape(-1,address_bytes)
            encoded[:,address_bytes:2*address_bytes]=np.frombuffer(b''.join(encode_address(v,address_bytes) for v in b),np.uint8).reshape(-1,address_bytes)
            encoded[:,-1]=lab.astype(np.uint8)
            old=seen[ix];assert np.array_equal(keys[ix[old]],encoded[old]),'Cross-chunk original tuple hash alias'
            fresh=ix[~old]
            assert np.array_equal(fresh,np.arange(first_cursor,first_cursor+len(fresh))), 'Old first-seen key order mismatch'
            first_cursor+=len(fresh)
            assert np.array_equal(y[ix],lab==1)
            keys[ix]=encoded;seen[ix]=True
        assert seen.all() and first_cursor==len(ids)
        blob=keys.reshape(-1).copy();offsets=np.arange(len(ids)+1,dtype=np.int64)*w
    else:
        raw=pd.read_csv(paths[0]);raw_rows=len(raw)
        col='url' if 'url' in raw else 'URL'
        union=None
        if ds=='url':
            label='type' if 'type' in raw else 'url_type'
            member=(raw[label].to_numpy()!=0) if raw[label].dtype.kind in 'iub' else ~raw[label].astype(str).str.lower().isin(['benign','good','0']).to_numpy()
            union=pd.DataFrame({'url':raw[col],'member':member}).groupby('url',dropna=False).member.max()
        raw=raw.drop_duplicates(col).reset_index(drop=True)
        assert raw[col].notna().all(),'Do not silently invent a raw key for NaN'
        hid=pd.util.hash_pandas_object(raw[col],index=False).to_numpy(np.uint64)
        yy=raw['label'].to_numpy()==1 if ds=='shalla' else raw[col].map(union).to_numpy(np.bool_)
        assert np.array_equal(ids,hid) and np.array_equal(y,yy)
        blob,offsets=pack([s.encode('utf-8') for s in raw[col].astype(str)])
    assert offsets[-1]==len(blob) and len(offsets)==len(ids)+1
    out.parent.mkdir(parents=True,exist_ok=True);np.savez(out,blob=blob,offsets=offsets)
    save(ROOT/f'results/raw_{ds}.json',dict(status='complete',dataset=ds,raw_rows=raw_rows,keys=len(ids),members=int(y.sum()),schema_width=width(ds),keys_over_width=int((np.diff(offsets)>width(ds)).sum()),raw_key_blob_bytes=blob.nbytes,offsets_bytes=offsets.nbytes,ids_sha256=ah(ids),labels_sha256=ah(y),prepared_sha256=sha(out),source_hashes={str(p.relative_to(BLOOM)):sha(p) for p in paths},member_verification_index_built=False,wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    print('RAW_COMPLETE',ds,len(ids),round(time.perf_counter()-start,3),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=DATASETS);a=p.parse_args()
    try:prepare(a.dataset)
    except Exception as e:save(ROOT/f'results/raw_{a.dataset}.failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:500]));raise

"""Round16 configuration; no installed-environment changes."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[v]='1'
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
WR=ROOT.parent
BLOOM=WR.parent
sys.path.insert(0,str(ROOT/'.deps/py312'))
DS='url'; KIB=128; REPS=3; VALUE_BYTES=4096
LEARN=50_000; TAIL=150_000; POS=16_667
WORKLOADS=('zipf','once')
METHODS=('Direct','BFCache','Gama','RA6','Replay')
CACHES={'fit':1024*1024*1024,'pressure':8*1024*1024}


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def ah(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()


def save(p,r):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n');tmp.replace(p)


def key_bytes(i):return int(i).to_bytes(8,'big')


def db_options(cache_bytes,create=False):
    import rocksdict as R
    cache=R.Cache(cache_bytes)
    table=R.BlockBasedOptions();table.set_block_cache(cache)
    table.set_bloom_filter(10.,False)
    table.set_cache_index_and_filter_blocks(True)
    table.set_block_size(4096)
    opts=R.Options(raw_mode=True);opts.create_if_missing(create)
    opts.enable_statistics();opts.set_block_based_table_factory(table)
    # Keep default compression, compaction and read caching; no direct-I/O trick.
    return opts,cache


def stats(opts):
    import re
    text=opts.get_statistics()
    counts={m.group(1):int(m.group(2)) for m in re.finditer(r'^(\S+) COUNT : (\d+)$',text,re.M)}
    return counts,text

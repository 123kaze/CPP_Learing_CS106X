"""Bounded serial timing protocol, importing the frozen exact round55 implementation."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[v]='1'
import sys,json,time,hashlib,resource,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BLOOM=ROOT.parents[1]
WR=ROOT.parent
sys.path.insert(0,str(WR/'round55_exact_full_main_v4/src'))
import common55 as C
np=C.np
SETTINGS=(('cod',1024),('caida',256),('shalla',1024),('url',128),('caida_flow',24),('mawi2020_flow',24),('mawi2021_flow',24),('mawi2022_flow',24))
METHODS=('Gama','Replay','RA6')
REPS=3


def order(rep):
    return METHODS[rep:]+METHODS[:rep]


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    assert not path.exists(),path
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    tmp.rename(path)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def read(path):return json.loads(path.read_text())


def reference(ds,kib):
    m=C.case_manifest();st=next(s for s in m['settings'] if (s['dataset'],s['budget_kib'])==(ds,kib))
    w='真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部'
    ix=next(i for i,c in enumerate(st['cases']) if c['seed']==0 and c['workload']==w)
    p=C.ROOT/f'results/{ds}_{kib}/case_{ix:03d}.json'
    return p,read(p)


def freeze_check(inputs=False):
    f=read(ROOT/'plan/freeze.json')
    for group in ('sources','inputs') if inputs else ('sources',):
        for name,digest in f[group].items():assert sha(BLOOM/name)==digest,name
    return f


def owner_bytes(array):
    seen=set()
    while isinstance(array.base,np.ndarray):
        assert id(array) not in seen
        seen.add(id(array));array=array.base
    return dict(logical_owner_payload_bytes=int(array.nbytes),owner_physical_bytes=sys.getsizeof(array),owns_data=bool(array.flags.owndata))


def check_regression(row,old):
    for field in ('trees','frac','fp','flags_sha','cache_sha','total_bytes','cache_bytes','cache_slots'):
        assert row[field]==old[field],(field,row[field],old[field])
    assert row['member_fn']==row['member_index_bytes']==0
    assert row['total_bytes']<=row['budget_bytes']

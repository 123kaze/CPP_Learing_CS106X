"""Round53 inputs and utilities. Never call legacy Setup or safe-prefix preparation."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[v]='1'
import sys,time,json,hashlib
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]; WR=ROOT.parent; BLOOM=WR.parent
for p in ('round6_bucket/src','round12_nomodel/src','round19_gt_fix/src'):
    sys.path.insert(0,str(WR/p))
import holdout6  # registration only
import ra6
import baseline as BF
from summarize19 import summarize19
import numpy as np
E5=ra6.E5; RA=ra6.RA; C=E5.C
BUDGETS={**E5.BUDGETS,'mawi2024_flow':(16,24,32,128)}
DATASETS=('url','caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow','mawi2024_flow','cod','caida','shalla')
WORKLOADS=(('每key一次',('once',)),('uniform-全部',('uniform',None)),('zipf1.0-全部',('zipf',None,1.0)))
METHODS=('Gama','Gama+10%','Replay','RA-global','RA-PLBF-GT19','BF+Exact','PlainBF')


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def ah(a):return hashlib.sha256(memoryview(np.ascontiguousarray(a)).cast('B')).hexdigest()


def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    tmp.replace(p)


def raw_paths(ds):
    if ds=='cod':return [BLOOM/'LBF-Gama/dataset/raw/cod'/f for f in ('train.csv','test.csv')]
    if ds in ('caida','caida_flow'):return [WR/'data/caida.csv']
    if ds in ('mawi2020_flow','mawi2021_flow'):return [WR/'data'/f'{ds.removesuffix("_flow")}.csv']
    if ds.endswith('_flow'):return [WR/'round2_backlog/data'/f'{ds.removesuffix("_flow")}.csv']
    return [WR/'round2_backlog/data'/('shalla_combined.csv' if ds=='shalla' else 'malicious_phish_full.csv')]


def inputs(ds):
    paths=[C.CACHE/ds/f for f in ('data.npz','scores.npz','gama_scores.npz','model200.txt')]
    if ds.endswith('_flow'):paths.append(C.CACHE/ds/'trace.npy')
    paths+=raw_paths(ds)
    ref=WR/('round6_bucket/results/holdout/round5_methods' if ds=='mawi2024_flow' else 'round5_dp/results')
    paths += [ref/f'rows_{ds}_{k}.csv' for k in BUDGETS[ds]]
    return paths


def width(ds):return 33 if ds=='caida_flow' else 9 if ds.endswith('_flow') else 8 if ds in ('cod','caida') else 128


def check_sources():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in f['sources'].items():assert sha(BLOOM/p)==h,p
    return f


def check_inputs(ds):
    f=check_sources()
    for p in inputs(ds):assert sha(p)==f['inputs'][str(p.relative_to(BLOOM))],str(p)


@contextmanager
def no_index():
    def forbidden(*a,**k):raise AssertionError('Round53 forbids member verification index/safe-prefix preparation')
    targets=[(C,'Setup'),(C,'cache_entry_bits'),(E5.R,'load_setup'),(E5,'load'),(E5.E,'load'),(E5.E.CC,'safe_prefix_lengths')]
    before=[(obj,name,getattr(obj,name)) for obj,name in targets]
    for obj,name,_ in before:setattr(obj,name,forbidden)
    try:yield
    finally:
        for obj,name,value in before:setattr(obj,name,value)


class Scores:
    """Load one frozen prefix at a time, avoiding a second full dataset-sized score bank."""
    def __init__(self,ds):self.path=C.CACHE/ds/'gama_scores.npz'
    def __getitem__(self,t):
        with np.load(self.path,allow_pickle=False) as f:return f[f't{t}']


def load(ds):
    start=time.perf_counter()
    with np.load(C.CACHE/ds/'data.npz',allow_pickle=False) as f:ids,y=f['ids'],f['y']
    split=C.make_split(ids,y,ds)
    with np.load(C.CACHE/ds/'scores.npz',allow_pickle=False) as f:score=f['score']
    hashes=C.splitmix64(ids^np.uint64(C.H1_SALT))
    s=SimpleNamespace(name=ds,ids=ids,y=y,split=split,h1m=hashes[y],h1q=hashes[split['neg_test']],q_ids=ids[split['neg_test']],q_score=score[split['neg_test']])
    assert not hasattr(s,'member_hashes') and not hasattr(s,'cache_cost')
    with np.load(ROOT/f'cache/{ds}.npz',allow_pickle=False) as f:blob,offsets=f['blob'],f['offsets']
    m=json.loads((ROOT/f'results/raw_{ds}.json').read_text())
    assert sha(ROOT/f'cache/{ds}.npz')==m['prepared_sha256'] and len(offsets)==len(ids)+1
    qi=np.flatnonzero(split['neg_test']);mi=np.flatnonzero(y)
    return s,Scores(ds),blob,offsets,qi,mi,time.perf_counter()-start


def workloads(ds):return (('真实轨迹',None),) if ds.endswith('_flow') else WORKLOADS

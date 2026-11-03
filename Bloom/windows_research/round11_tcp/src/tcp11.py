"""Round 11 plumbing: protocol-consistent (TCP-only) real traces, see plan/design-freeze.md.

usage: tcp11.py prepare                      build data.npz / trace.npy, train and score (round-2 pipeline)
       tcp11.py run <script.py> [args...]    run a frozen runner unchanged with the datasets registered
       tcp11.py method <m> <dataset>         run5 | run6 | run10 | grid10 in-process, with only the module's
                                             output root moved to results/<m>/ (their results/ paths are
                                             hard-coded inside the frozen rounds).  One method per process:
                                             importing run10 replaces the engine's cache module.
Datasets are registered exactly like round6_bucket/src/holdout6.py registers mawi2024_flow; budgets
follow the frozen rule (1, 2, 4, 12 bits per member, rounded up to KiB) and are added to engine5.
"""
import json
import runpy
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WR = HERE.parents[1]
BLOOM = WR.parent
R2 = WR / 'round2_backlog'
sys.path.insert(0, str(R2 / 'src'))
import prepare_datasets as D  # noqa: E402  (sets the round-2 cache and registry)

W = 0.5
BITS = (1, 2, 4, 12)
SOURCES = {
    'caida_tcp_flow': BLOOM / 'learned_adaptive_hybrid/external/How-to-Train-Your-Filter/data/raw/caida.csv',
    'mawi2020_tcp_flow': BLOOM / 'learned_adaptive_hybrid/external/mawi/mawi2020.csv',
    'mawi2021_tcp_flow': WR / 'data/mawi2021.csv',
    'mawi2022_tcp_flow': R2 / 'data/mawi2022.csv',
}
META = ROOT / 'results' / 'datasets.json'

for name in SOURCES:
    D.C.DATASETS[name] = dict(raw=R2 / 'data', member_train=.5, neg_cuts=(.1, .2))
    D.R.C.DATASETS[name] = D.C.DATASETS[name]


def budgets(members):
    return tuple(int(-(-members * b // (8 * 1024))) for b in BITS)


def register_budgets():
    sys.path.insert(0, str(WR / 'round5_dp' / 'src'))
    import engine5 as E5
    meta = json.loads(META.read_text())
    for name, m in meta.items():
        E5.BUDGETS[name] = tuple(m['budgets_kib'])
        E5.HIGH[name] = m['budgets_kib'][-1]


def build(name, src):
    raw = pd.read_csv(src, usecols=['Source', 'Destination', 'Label'])
    tcp = raw[raw['Label'].to_numpy() == 0]
    flow = tcp['Source'].astype(str) + '>' + tcp['Destination'].astype(str)
    codes, uniq = pd.factorize(flow, sort=False)
    n = len(codes)
    cut = int(n * W)
    y = np.zeros(len(uniq), bool)
    y[codes[:cut]] = True
    first = ~pd.Series(codes).duplicated().to_numpy()
    X = tcp.loc[first, ['Source', 'Destination']].to_numpy(np.float32)   # first packet of every flow, in code order
    ids = pd.util.hash_pandas_object(pd.Series(uniq), index=False).to_numpy(np.uint64)
    assert len(np.unique(ids)) == len(ids)
    folder = D.C.CACHE / name
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(folder / 'data.npz', ids=ids, y=y, X=X, features=np.array(['src', 'dst']))
    np.save(folder / 'trace.npy', codes[cut:].astype(np.int64))
    pair = X[:, 0].astype(np.float64) * 2 ** 33 + X[:, 1].astype(np.float64)
    shared_exact = int(pd.Index(uniq[~y]).isin(pd.Index(uniq[y])).sum())   # 0 by construction
    shared_model = int(np.isin(pair[~y], pair[y]).sum())
    tail = codes[cut:]
    return dict(source=str(src.relative_to(BLOOM)), packets=int(len(raw)), tcp_packets=int(n), flows=int(len(uniq)),
                members=int(y.sum()), negatives=int((~y).sum()), tail_packets=int(len(tail)),
                tail_packets_on_negatives=int((~y[tail]).sum()),
                negatives_sharing_exact_key_with_member=shared_exact,
                negatives_sharing_model_input_with_member=shared_model, budgets_kib=list(budgets(int(y.sum()))))


def prepare():
    META.parent.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META.read_text()) if META.exists() else {}
    for name, src in SOURCES.items():
        if name not in meta:
            meta[name] = build(name, src)
            META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
            print(name, meta[name], flush=True)
        D.R.prepare(name, threads=8)


def method(m, ds):
    register_budgets()
    import engine5 as E5
    kib = list(E5.BUDGETS[ds])
    dirs = dict(run5=WR / 'round5_dp' / 'src', run6=WR / 'round6_bucket' / 'src',
                run10=WR / 'round10_fpcache' / 'src', grid10=WR / 'round10_fpcache' / 'src')
    sys.path.insert(0, str(dirs[m]))
    mod = __import__(m)
    mod.ROOT = ROOT / 'results' / m
    mod.ROOT.mkdir(parents=True, exist_ok=True)
    if m == 'run5':
        mod.run(ds, kib, 10_000_000, 1)
    elif m == 'run6':
        mod.run(ds, kib, 10_000_000, 1, 'main')
    elif m == 'run10':
        mod.run(ds, kib, 10_000_000, 1, 'main')
    else:
        import cache_fp
        E5.K = cache_fp
        mod.run(ds, kib, 1, 'LearnGrid-fp64', 'grid')


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'method':
        method(sys.argv[2], sys.argv[3])
    else:
        register_budgets()
        script = sys.argv[2]
        sys.argv = [script] + sys.argv[3:]
        sys.path.insert(0, str(Path(script).resolve().parent))
        runpy.run_path(script, run_name='__main__')

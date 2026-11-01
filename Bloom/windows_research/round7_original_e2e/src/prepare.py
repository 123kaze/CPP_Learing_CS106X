"""Fix common streams and canonical member/key order; no measured method runs here."""
import shared as S
import sys
import time
import numpy as np

sys.path.insert(0, str(S.ROOT.parent / 'round6_bucket' / 'src'))
import e789 as J


def prepare(ds):
    folder = S.ROOT / 'inputs' / ds
    if (folder / 'meta.json').exists():
        return
    t0 = time.perf_counter()
    setup = J.R.load_setup(ds)
    name = '真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部'
    spec = None if ds.endswith('_flow') else dict(J.E5.workload_specs(len(setup.h1q)))[name]
    stream = J.E5.base_stream(setup, name, spec, 0)
    n = len(stream) // 4
    folder.mkdir(parents=True, exist_ok=True)
    np.save(folder / 'learn.npy', stream[:n])
    np.save(folder / 'tail.npy', stream[n:])
    nm = len(setup.h1m)
    mixed = J.mixed(stream[n:n + 200000], nm, .1, np.random.default_rng(71000))
    np.save(folder / 'mixed.npy', mixed)
    np.save(folder / 'member_ids.npy', setup.ids[setup.y])
    np.save(folder / 'query_ids.npy', setup.q_ids)
    S.save(folder / 'meta.json', dict(dataset=ds, workload=name, seed=0, members=nm,
                                     negative_pool=len(setup.h1q), learning_queries=n,
                                     tail_queries=len(stream) - n, prep_s=time.perf_counter() - t0,
                                     learn_sha256=S.digest(folder / 'learn.npy'),
                                     tail_sha256=S.digest(folder / 'tail.npy'),
                                     mixed_sha256=S.digest(folder / 'mixed.npy')))
    print(f'PREPARED {ds}: {len(stream)} queries', flush=True)


if __name__ == '__main__':
    for ds in sys.argv[1:]:
        prepare(ds)

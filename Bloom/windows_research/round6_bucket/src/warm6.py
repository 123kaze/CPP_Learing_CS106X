"""RA6-warm: RA6's structure, but the cache starts the evaluation segment in the state it reaches
after replaying the learning period (instead of empty).

This matches what learned stacked carries into deployment (its negative Bloom layer is built from
the learning-period FPs).  Selection is unchanged -- the same select6 call as the main table, so the
cold-cache FP of every case must equal the main-table RA6 row (asserted).  Streams, learning period
(first 25%), evaluation segment and the probe replay (F-C, the structure's own FPs) are those of
the main table.
usage: warm6.py <dataset> [budgets]  -> results/warm/rows_<ds>_<kib>.csv
"""
import csv
import sys
import time
from pathlib import Path
import numpy as np
import ra6

ROOT = Path(__file__).resolve().parents[1]
E5, RA = ra6.E5, ra6.RA
K = E5.K
COLS = ('dataset', 'budget_kib', 'workload', 'seed', 'method', 'trees', 'cache_bytes', 'fp_tail_cold', 'fp_tail')


def main_fp(ds, kib):
    f = ROOT / 'results' / 'main' / f'rows_{ds}_{kib}.csv'
    return {(r['workload'], int(r['seed'])): int(r['fp_tail'])
            for r in csv.DictReader(open(f, encoding='utf-8')) if r['method'] == 'RA6'}


def warm_fp(c, learn, tail, setup, safe):
    st = c['structure']
    if not c['cache_bytes']:
        return int(st.fp_static[tail].sum())
    spec = K.layout(c['cache_bytes'], E5.PREFIX, E5.WAYS)
    data = K.allocate(spec)
    args = (setup.h1q, safe, st.fp_static, data, spec['buckets'], E5.PREFIX, spec['Q'], spec['ob'], spec['slot_bits'],
            E5.WAYS, spec['handbits'], 2 ** 62, np.zeros(0, np.int64), np.zeros(0, np.bool_))
    K.replay(np.asarray(learn, np.int64), *args)
    return int(K.replay(np.asarray(tail, np.int64), *args)[0])


def run(ds, budgets):
    setup, scores, safe = E5.load(ds)
    real = ds.endswith('_flow')
    specs = [('真实轨迹', None)] if real else E5.workload_specs(len(setup.h1q))
    seeds = 1 if real else 5
    out = ROOT / 'results' / 'warm'
    out.mkdir(parents=True, exist_ok=True)
    for kib in budgets:
        ref = main_fp(ds, kib)
        dest = out / f'rows_{ds}_{kib}.csv'
        done = set()
        if dest.exists():
            done = {(r['workload'], int(r['seed'])) for r in csv.DictReader(open(dest, encoding='utf-8'))}
        for name, spec in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                t0 = time.perf_counter()
                base = E5.base_stream(setup, name, spec, seed)
                n = len(base) // 4
                learn, base_tail = base[:n], base[n:]
                c, _ = ra6.select6(setup, scores, RA.ra4.summarize(learn, True), kib, len(base_tail))
                tail = E5.tail_for(c, name, base_tail, seed)
                cold = int(E5.evaluate(c, tail, setup, safe)['fp'])
                assert cold == ref[name, seed], ('main-table RA6 not reproduced', ds, kib, name, seed, cold, ref[name, seed])
                row = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, method='RA6-warm', trees=c['trees'],
                           cache_bytes=int(c['cache_bytes']), fp_tail_cold=cold,
                           fp_tail=warm_fp(c, learn, tail, setup, safe))
                new = not dest.exists()
                with dest.open('a', encoding='utf-8', newline='') as fh:
                    w = csv.DictWriter(fh, fieldnames=COLS)
                    if new:
                        w.writeheader()
                    w.writerow(row)
                print(f'{ds} {kib}KiB {name} s{seed} {time.perf_counter() - t0:.1f}s cold={cold} warm={row["fp_tail"]}', flush=True)
        print(f'COMPLETE {ds}/{kib}', flush=True)
        E5._TREE.clear()
        E5.R._GSETUPS.clear()


if __name__ == '__main__':
    run(sys.argv[1], [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else E5.BUDGETS[sys.argv[1]])

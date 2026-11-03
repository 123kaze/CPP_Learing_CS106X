"""Why is the fingerprint cache worse?  Fewer slots vs no safe-prefix generalisation (diagnostic).

For every round-6 main-table case, RA6's own structure (index-based selection, as round 6) is
rebuilt and its tail replayed with three caches of exactly the same byte size:
  idx   frozen cache5 with the member index: matches on the key's safe prefix (shortest prefix no
        member shares), so one entry also answers every other negative with that prefix; keys
        whose safe prefix is longer than 40 bits are not cached.  Must reproduce round 6.
  p40   cache5's layout and slot count, but every safe length set to 40: exact 40-bit match, no
        generalisation, no bypass (index-free, false negatives possible; diagnostic only).
  fp64  cache_fp: exact 64-bit fingerprints, about 2/3 of the slots.
idx -> p40 is the generalisation effect, p40 -> fp64 the slot effect.  RA6-fp64 (round 10 main)
additionally re-selects the configuration for the fingerprint cache.
usage: decompose.py --dataset <ds> [--budgets ...]   -> results/decompose/rows_<ds>_<kib>.csv
"""
import argparse
import csv
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'round6_bucket' / 'src'))
import cache_fp as F  # noqa: E402
import ra6  # noqa: E402

E5, RA, C5 = ra6.E5, ra6.RA, F.C5
COLS = ['dataset', 'budget_kib', 'workload', 'seed', 'trees', 'cache_alloc_bytes', 'slots_idx', 'slots_fp64',
        'fp_idx', 'fp_p40', 'fp_fp64', 'bypass_idx', 'distinct_fp_keys', 'static_fp']


def run(ds, budgets, seeds=5):
    setup, scores, safe = E5.load(ds)
    safe40 = np.full_like(safe, 40)
    specs = [('真实轨迹', None)] if ds.endswith('_flow') else E5.workload_specs(len(setup.h1q))
    seeds = 1 if ds.endswith('_flow') else seeds
    r6 = {}
    out = ROOT / 'results' / 'decompose'
    out.mkdir(parents=True, exist_ok=True)
    for kib in budgets:
        with open(HERE.parents[1] / 'round6_bucket' / 'results' / 'main' / f'rows_{ds}_{kib}.csv', encoding='utf-8') as fh:
            r6 = {(r['workload'], int(r['seed'])): int(r['fp_tail']) for r in csv.DictReader(fh) if r['method'] == 'RA6'}
        dest = out / f'rows_{ds}_{kib}.csv'
        done = set()
        if dest.exists():
            with dest.open(encoding='utf-8') as fh:
                done = {(r['workload'], int(r['seed'])) for r in csv.DictReader(fh)}
        for name, spec in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                base = E5.base_stream(setup, name, spec, seed)
                n = len(base) // 4
                lm = RA.ra4.summarize(base[:n], True)
                c, info = ra6.select6(setup, scores, lm, kib, len(base) - n)
                tail = E5.tail_for(c, name, base[n:], seed)
                fps = c['structure'].fp_static
                cb = c['cache_bytes']
                if cb:
                    a = C5.simulate(tail, setup.h1q, safe, fps, cb, E5.PREFIX, E5.WAYS, collect=True)
                    b = C5.simulate(tail, setup.h1q, safe40, fps, cb, E5.PREFIX, E5.WAYS)
                    f = F.simulate(tail, setup.h1q, None, fps, cb)
                    assert a['slots'] == b['slots']
                else:
                    z = int(fps[tail].sum())
                    a = dict(fp=z, slots=0, bypasses=0, distinct_fp_keys=int(np.unique(tail[fps[tail]]).size))
                    b = f = dict(fp=z, slots=0)
                assert a['fp'] == r6[name, seed], (name, seed, a['fp'], r6[name, seed])
                row = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, trees=c['trees'], cache_alloc_bytes=cb,
                           slots_idx=a['slots'], slots_fp64=f['slots'], fp_idx=a['fp'], fp_p40=b['fp'], fp_fp64=f['fp'],
                           bypass_idx=a['bypasses'], distinct_fp_keys=a['distinct_fp_keys'],
                           static_fp=int(fps[tail].sum()))
                new = not dest.exists()
                with dest.open('a', encoding='utf-8', newline='') as fh:
                    w = csv.DictWriter(fh, fieldnames=COLS)
                    if new:
                        w.writeheader()
                    w.writerow(row)
                print(ds, kib, name, seed, a['fp'], b['fp'], f['fp'], flush=True)
        E5._TREE.clear()
        E5.R._GSETUPS.clear()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets')
    a = p.parse_args()
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E5.BUDGETS[a.dataset])

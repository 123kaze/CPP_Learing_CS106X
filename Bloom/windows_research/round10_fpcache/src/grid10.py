"""LearnGrid with the fingerprint cache, so that RA6-fp64 has a like-for-like grid reference.

Round 5's LearnGrid (round5_dp/src/run5.py) builds every (trees, cache fraction) candidate,
replays each on the learning period (engine5.replay_best, early stopping) and deploys the best.
Here the engine's cache module is replaced exactly as in run10.py, so candidate slot counts,
the learning replay and the tail replay all use the 64-bit fingerprint cache.
--cache index keeps the frozen cache5 and must reproduce round 5's LearnGrid rows.
usage: grid10.py --dataset <ds> [--budgets ...] [--cache fp64|index]   -> results/<grid|grid_check_index>/
"""
import argparse
import csv
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'round6_bucket' / 'src'))
import cache_fp as F  # noqa: E402
import ra6  # noqa: E402

E5 = ra6.E5
COLS = ['dataset', 'budget_kib', 'workload', 'seed', 'method', 'trees', 'frac', 'cache_alloc_bytes', 'fp_tail',
        'select_s']


def run(ds, budgets, seeds, method, tag):
    setup, scores, safe = E5.load(ds)
    specs = [('真实轨迹', None)] if ds.endswith('_flow') else E5.workload_specs(len(setup.h1q))
    seeds = 1 if ds.endswith('_flow') else seeds
    out = ROOT / 'results' / tag
    out.mkdir(parents=True, exist_ok=True)
    for kib in budgets:
        dest = out / f'rows_{ds}_{kib}.csv'
        done = set()
        if dest.exists():
            with dest.open(encoding='utf-8') as fh:
                done = {(r['workload'], int(r['seed'])) for r in csv.DictReader(fh)}
        cands = E5.candidates(setup, scores, kib)
        for name, spec in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                base = E5.base_stream(setup, name, spec, seed)
                n = len(base) // 4
                ts = time.perf_counter()
                grid, _ = E5.replay_best(cands, base[:n], setup, safe)
                sel = time.perf_counter() - ts
                tail = E5.tail_for(grid, name, base[n:], seed)
                fp = E5.evaluate(grid, tail, setup, safe)['fp']
                row = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, method=method, trees=grid['trees'],
                           frac=grid['frac'], cache_alloc_bytes=grid['cache_bytes'], fp_tail=fp, select_s=round(sel, 3))
                new = not dest.exists()
                with dest.open('a', encoding='utf-8', newline='') as fh:
                    w = csv.DictWriter(fh, fieldnames=COLS)
                    if new:
                        w.writeheader()
                    w.writerow(row)
                print(ds, kib, name, seed, method, fp, grid['trees'], grid['frac'], f'{sel:.1f}s', flush=True)
        print(f'COMPLETE {ds}/{kib}', flush=True)
        E5._TREE.clear()
        E5.R._GSETUPS.clear()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets')
    p.add_argument('--seeds', type=int, default=5)
    p.add_argument('--cache', choices=('fp64', 'index'), default='fp64')
    a = p.parse_args()
    if a.cache == 'fp64':
        E5.K = F
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E5.BUDGETS[a.dataset], a.seeds,
        'LearnGrid-fp64' if a.cache == 'fp64' else 'LearnGrid', 'grid' if a.cache == 'fp64' else 'grid_check_index')

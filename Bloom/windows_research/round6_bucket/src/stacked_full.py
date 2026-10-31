"""Learned stacked on the round-5 engine over the full workload set (all budgets, workloads, seeds).

Same baseline as the E7 supplement (e7_extra.py): Gama's tree count; `frac` of the budget moved
from the base PLBF to two side layers (negative BF of the learning-period FP keys, then a positive
BF of the members it hits); frac x b2 chosen on the second half of the learning period, Gama when
no side layer helps (round-2 protocol).  Streams, learning period (first 25%) and evaluation
segment are exactly those of the round-5/6 main tables; the probe workload replays the stacked
filter's own FPs (F-C).  Base structures do not depend on the stream, so they are built once per
(dataset, budget, frac).  Zero false negatives and the byte budget are asserted for every case.
usage: stacked_full.py <dataset> [budgets]  -> results/stacked/rows_<ds>_<kib>.csv
"""
import csv
import sys
import time
from pathlib import Path
import numpy as np
import e7_extra as X7

ROOT = Path(__file__).resolve().parents[1]
E5 = X7.E5
COLS = ('dataset', 'budget_kib', 'workload', 'seed', 'method', 'trees', 'frac', 'b2', 'used_bytes', 'fp_tail')


def stacked_fp(setup, bases, gama, kib, learn):
    """Round-2 selection; returns (fp flags over the pool, frac, b2, used bytes)."""
    split = len(learn) // 2
    counts = np.bincount(learn[split:], minlength=len(setup.h1q))
    best = (int(counts[gama['structure'].fp_static].sum()), 0., 0.)
    for f, (side, base) in bases.items():
        fl = base['structure'].fp_static
        known = np.unique(learn[:split][fl[learn[:split]]])
        for b2 in X7.B2S:
            L = X7.stacked_layers(setup, base, known, side, b2)
            if L is None:
                continue
            v = int(counts[L['fp']].sum())
            if (v, f, b2) < best:
                best = (v, f, b2)
    _, f, b2 = best
    if f:
        side, base = bases[f]
        fl = base['structure'].fp_static
        L = X7.stacked_layers(setup, base, np.unique(learn[fl[learn]]), side, b2)
        if L is not None:
            hit = X7.bf_query(setup.h1m, L['neg'], L['k2'])
            assert X7.bf_query(setup.h1m[hit], L['pos'], L['k3']).all(), 'stacked false negative'
            used = base['structure'].used_bytes - side + L['side']
            return L['fp'], f, b2, used
    return gama['structure'].fp_static, 0., 0., gama['structure'].used_bytes


def run(ds, budgets):
    setup, scores, safe = E5.load(ds)
    real = ds.endswith('_flow')
    specs = [('真实轨迹', None)] if real else E5.workload_specs(len(setup.h1q))
    seeds = 1 if real else 5
    out = ROOT / 'results' / 'stacked'
    out.mkdir(parents=True, exist_ok=True)
    for kib in budgets:
        dest = out / f'rows_{ds}_{kib}.csv'
        done = set()
        if dest.exists():
            done = {(r['workload'], int(r['seed'])) for r in csv.DictReader(open(dest, encoding='utf-8'))}
        cands = E5.candidates(setup, scores, kib)
        gama = E5.gama(cands)
        gt = gama['trees']
        bases = {}
        for f in X7.FRACS:
            side = int(kib * 1024 * f)
            b = E5.build(setup, scores, gt, kib, 0., cache_bytes=side, slots=0)
            if b is not None:
                bases[f] = (side, b)
        for name, spec in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                t0 = time.perf_counter()
                base = E5.base_stream(setup, name, spec, seed)
                n = len(base) // 4
                learn, tail = base[:n], base[n:]
                fp, f, b2, used = stacked_fp(setup, bases, gama, kib, learn)
                assert used <= kib * 1024
                if name == E5.PROBE:
                    tail = E5.E.probe_replay(tail, fp, 11000 + seed)
                row = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, method='LearnedStacked', trees=gt,
                           frac=f, b2=b2, used_bytes=int(used), fp_tail=int(fp[tail].sum()))
                new = not dest.exists()
                with dest.open('a', encoding='utf-8', newline='') as fh:
                    w = csv.DictWriter(fh, fieldnames=COLS)
                    if new:
                        w.writeheader()
                    w.writerow(row)
                print(f'{ds} {kib}KiB {name} s{seed} {time.perf_counter() - t0:.1f}s frac={f} b2={b2} fp={row["fp_tail"]}', flush=True)
        print(f'COMPLETE {ds}/{kib}', flush=True)
        E5._TREE.clear()
        E5.R._GSETUPS.clear()


if __name__ == '__main__':
    run(sys.argv[1], [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else E5.BUDGETS[sys.argv[1]])

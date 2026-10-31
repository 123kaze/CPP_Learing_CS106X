"""Learned stacked with the side layers built by the ORIGINAL Stacked Filter code.

Same protocol as stacked_full.py (Gama's tree count; `frac` of the budget taken from the base PLBF
for the side structure; frac chosen on the second half of the learning period; rebuilt on the whole
learning period; Gama when nothing helps), but the side structure is the unmodified
StackedFilter<BloomFilterLayer, BigIntElement> of bitbucket.org/HarvardDASlab/stackedfilters
(6e04ca6), driven by original_baselines/stacked/stacked_orig_driver (same binary as the
original-code baseline):
  positives = all members; negatives = learning-period keys the base accepts (its false
  positives), in descending learning frequency; cdf = cumulative share of their query mass;
  total size = the side budget in bits.  Its own optimizer picks the layers.
  Query: base accepts AND the stacked filter accepts.
Accounting: ceil(actual bits / 8) + one array header per layer.  The original optimizer may exceed
the size it was given; such a candidate is discarded (not truncated), and if the rebuilt choice
exceeds, the case falls back to Gama.  The library seeds its layer hashes from std::random_device,
so runs are not bit-reproducible.
usage: stacked_orig_side.py <dataset> [budgets]  -> results/stacked_orig/rows_<ds>_<kib>.csv
"""
import csv
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import numpy as np
import ra6

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT.parents[1] / 'original_baselines' / 'stacked' / 'stacked_orig_driver'
E5 = ra6.E5
FRACS = (.02, .05, .1, .2, .4, .6)
COLS = ('dataset', 'budget_kib', 'workload', 'seed', 'method', 'trees', 'frac', 'layers', 'side_bits', 'used_bytes',
        'rejected_over_size', 'fp_tail')


class Side:
    def __init__(self, setup, tmp):
        self.setup, self.tmp = setup, Path(tmp)
        setup.ids[setup.y].astype(np.uint64).tofile(self.tmp / 'pos.u64')
        setup.q_ids.astype(np.uint64).tofile(self.tmp / 'qry.u64')

    def build(self, base_fp, learn, side_bytes):
        """Original StackedFilter on the base's learning-period FPs; None if it does not fit."""
        keys, counts = np.unique(learn[base_fp[learn]], return_counts=True)
        if len(keys) == 0:
            return None
        order = np.argsort(-counts, kind='stable')
        self.setup.q_ids[keys[order]].astype(np.uint64).tofile(self.tmp / 'neg.u64')
        (np.cumsum(counts[order]) / counts.sum()).astype(np.float64).tofile(self.tmp / 'cdf.f64')
        p = subprocess.run([str(DRIVER), str(side_bytes * 8), *(str(self.tmp / f) for f in
                            ('pos.u64', 'neg.u64', 'cdf.f64', 'qry.u64', 'out.u8'))], capture_output=True, text=True)
        assert p.returncode == 0, ('stacked driver failed (member false negative or crash)', p.stderr[-300:])
        info = json.loads(p.stdout.strip().splitlines()[-1])
        cost = -(-info['actual_bits'] // 8) + info['layers'] * E5.K.ARRAY_HEADER
        if cost > side_bytes:
            return None
        acc = np.fromfile(self.tmp / 'out.u8', np.uint8).astype(bool)
        return dict(fp=base_fp & acc, layers=info['layers'], bits=info['actual_bits'], cost=cost)


def choose(side, bases, gama, learn):
    split = len(learn) // 2
    counts = np.bincount(learn[split:], minlength=len(gama['structure'].fp_static))
    best = (int(counts[gama['structure'].fp_static].sum()), 0.)
    rejected = 0
    for f, (sb, base) in bases.items():
        L = side.build(base['structure'].fp_static, learn[:split], sb)
        if L is None:
            rejected += 1
            continue
        best = min(best, (int(counts[L['fp']].sum()), f))
    f = best[1]
    if f:
        sb, base = bases[f]
        L = side.build(base['structure'].fp_static, learn, sb)
        if L is not None:
            return L['fp'], f, L['layers'], L['bits'], base['structure'].used_bytes - sb + L['cost'], rejected
        rejected += 1
    return gama['structure'].fp_static, 0., 0, 0, gama['structure'].used_bytes, rejected


def run(ds, budgets):
    setup, scores, safe = E5.load(ds)
    real = ds.endswith('_flow')
    specs = [('真实轨迹', None)] if real else E5.workload_specs(len(setup.h1q))
    seeds = 1 if real else 5
    out = ROOT / 'results' / 'stacked_orig'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        side = Side(setup, tmp)
        for kib in budgets:
            dest = out / f'rows_{ds}_{kib}.csv'
            done = set()
            if dest.exists():
                done = {(r['workload'], int(r['seed'])) for r in csv.DictReader(open(dest, encoding='utf-8'))}
            gama = E5.gama(E5.candidates(setup, scores, kib))
            bases = {}
            for f in FRACS:
                sb = int(kib * 1024 * f)
                b = E5.build(setup, scores, gama['trees'], kib, 0., cache_bytes=sb, slots=0)
                if b is not None:
                    bases[f] = (sb, b)
            for name, spec in specs:
                for seed in range(seeds):
                    if (name, seed) in done:
                        continue
                    t0 = time.perf_counter()
                    base = E5.base_stream(setup, name, spec, seed)
                    n = len(base) // 4
                    learn, tail = base[:n], base[n:]
                    fp, f, layers, bits, used, rej = choose(side, bases, gama, learn)
                    assert used <= kib * 1024
                    if name == E5.PROBE:
                        tail = E5.E.probe_replay(tail, fp, 11000 + seed)
                    row = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, method='LearnedStacked(orig layers)',
                               trees=gama['trees'], frac=f, layers=layers, side_bits=bits, used_bytes=int(used),
                               rejected_over_size=rej, fp_tail=int(fp[tail].sum()))
                    new = not dest.exists()
                    with dest.open('a', encoding='utf-8', newline='') as fh:
                        w = csv.DictWriter(fh, fieldnames=COLS)
                        if new:
                            w.writeheader()
                        w.writerow(row)
                    print(f'{ds} {kib}KiB {name} s{seed} {time.perf_counter() - t0:.1f}s frac={f} layers={layers} '
                          f'rejected={rej} fp={row["fp_tail"]}', flush=True)
            print(f'COMPLETE {ds}/{kib}', flush=True)
            E5._TREE.clear()
            E5.R._GSETUPS.clear()


if __name__ == '__main__':
    run(sys.argv[1], [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else E5.BUDGETS[sys.argv[1]])

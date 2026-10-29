"""Original Stacked Filter (bitbucket HarvardDASlab/stackedfilters) on the round-3 streams.

Per (dataset, budget, workload, seed): negatives = keys seen in the first 25% (learning
period), sorted by learning frequency, cdf = cumulative learning query share; total size =
the whole budget in bits; the filter answers every test-pool key once (it is static), tail
FP = sum over tail queries of the static flags.  Run with the project env.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'windows_research' / 'round3_ra_plbf' / 'src'))
import ra_plbf as RA  # noqa: E402

E = RA.E
DRIVER = HERE / 'stacked_orig_driver'


def run(ds, budgets, queries=10_000_000, seeds=5):
    setup, scores, _ = E.load(ds)
    out = HERE / 'out' / ds
    out.mkdir(parents=True, exist_ok=True)
    specs = [('真实轨迹', None, 'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
    seeds = 1 if ds.endswith('_flow') else seeds
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        setup.ids[setup.y].astype(np.uint64).tofile(tmp / 'pos.u64')
        setup.q_ids.astype(np.uint64).tofile(tmp / 'qry.u64')
        for kib in budgets:
            dest = out / f'{kib}.json'
            obj = json.loads(dest.read_text()) if dest.exists() else dict(rows=[])
            done = {(r['workload'], r['seed']) for r in obj['rows']}
            # Gama structure of this budget: only drives the probe-replay stream, exactly as in round 3
            gama = min((c for c in (E.build(setup, scores, t, kib, 0.) for t in E.R.GAMA_TREES) if c),
                       key=lambda c: (c['structure'].est_fpr, c['trees']))
            for name, spec, family in specs:
                for seed in range(seeds):
                    if (name, seed) in done:
                        continue
                    t0 = time.perf_counter()
                    stream = E.stream_for(setup, name, spec, family, seed, queries, gama['structure'])
                    n = len(stream) // 4
                    keys, counts = np.unique(stream[:n], return_counts=True)
                    order = np.argsort(-counts, kind='stable')
                    setup.q_ids[keys[order]].astype(np.uint64).tofile(tmp / 'neg.u64')
                    (np.cumsum(counts[order]) / n).astype(np.float64).tofile(tmp / 'cdf.f64')
                    p = subprocess.run([str(DRIVER), str(kib * 1024 * 8), str(tmp / 'pos.u64'), str(tmp / 'neg.u64'),
                                        str(tmp / 'cdf.f64'), str(tmp / 'qry.u64'), str(tmp / 'out.u8')],
                                       capture_output=True, text=True)
                    rec = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, method='Stacked(original)')
                    if p.returncode != 0:
                        rec.update(error=(p.stderr or p.stdout)[-500:])
                    else:
                        info = json.loads(p.stdout.strip().splitlines()[-1])
                        fp = np.fromfile(tmp / 'out.u8', np.uint8).astype(bool)
                        tail = stream[n:]
                        rec.update(info, fp_tail=int(fp[tail].sum()), evaluation_queries=len(tail),
                                   over_budget=info['actual_bits'] > info['total_bits'],
                                   learning_negatives=len(keys))
                    rec['seconds'] = time.perf_counter() - t0
                    obj['rows'].append(rec)
                    dest.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
                    print(ds, kib, name, seed, {k: rec.get(k) for k in ('fp_tail', 'actual_bits', 'layers', 'error')},
                          f"{rec['seconds']:.1f}s", flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets')
    a = p.parse_args()
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E.BUDGETS[a.dataset])

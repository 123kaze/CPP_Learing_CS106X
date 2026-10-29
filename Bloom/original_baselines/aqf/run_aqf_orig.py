"""Official AdaptiveQF (splatlab/adaptiveqf, arm64 port) on the round-3 streams.

Per (dataset, budget, workload, seed): members inserted, the whole stream replayed in
order, every false positive adapted through the official reverse-map wrapper; tail FP =
false positives in the last 75% (the first 25% is the shared learning period).
Run with the project env.
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
DRIVER = HERE / 'aqf_orig_driver'


def run(ds, budgets, queries=10_000_000, seeds=5):
    setup, scores, _ = E.load(ds)
    out = HERE / 'out' / ds
    out.mkdir(parents=True, exist_ok=True)
    specs = [('真实轨迹', None, 'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
    seeds = 1 if ds.endswith('_flow') else seeds
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        setup.ids[setup.y].astype(np.uint64).tofile(tmp / 'pos.u64')
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
                    setup.q_ids[stream].astype(np.uint64).tofile(tmp / 'stream.u64')
                    p = subprocess.run([str(DRIVER), str(kib * 1024), str(tmp / 'pos.u64'), str(tmp / 'stream.u64'), str(n)],
                                       capture_output=True, text=True)
                    rec = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, method='AdaptiveQF(original)')
                    if p.returncode != 0:
                        rec.update(error=(p.stderr or p.stdout)[-500:])
                    else:
                        rec.update(json.loads(p.stdout.strip().splitlines()[-1]), evaluation_queries=len(stream) - n)
                    rec['seconds'] = time.perf_counter() - t0
                    obj['rows'].append(rec)
                    dest.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
                    print(ds, kib, name, seed, {k: rec.get(k) for k in ('fp_tail', 'rbits', 'size_bytes', 'infeasible', 'adapt_failures', 'error')},
                          f"{rec['seconds']:.1f}s", flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets')
    a = p.parse_args()
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E.BUDGETS[a.dataset])

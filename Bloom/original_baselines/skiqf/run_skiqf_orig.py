"""SkiQF and HybridSkiQF (saltsystemslab/SkiRentalAdaptiveQF, arm64 port) on the round-3 streams.

Per (dataset, budget, workload, seed): member hashes inserted, the whole stream replayed in
order; on every false positive the variant decides to rent (count) or buy (adapt);
tail FP = false positives in the last 75%.  break-even count 2 (the paper's default runs).
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
DRIVER = HERE / 'skiqf_orig_driver'
VARIANTS = (('ski', 'SkiQF(original)'), ('hybrid', 'HybridSkiQF(original)'))
BREAK_EVEN = 2


def run(ds, budgets, queries=10_000_000, seeds=5):
    setup, scores, _ = E.load(ds)
    out = HERE / 'out' / ds
    out.mkdir(parents=True, exist_ok=True)
    specs = [('真实轨迹', None, 'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
    seeds = 1 if ds.endswith('_flow') else seeds
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        setup.h1m.astype(np.uint64).tofile(tmp / 'pos.u64')   # 64-bit key hashes (QF_KEY_IS_HASH)
        for kib in budgets:
            dest = out / f'{kib}.json'
            obj = json.loads(dest.read_text()) if dest.exists() else dict(rows=[])
            done = {(r['workload'], r['seed'], r['method']) for r in obj['rows']}
            # Gama structure of this budget: only drives the probe-replay stream, exactly as in round 3
            gama = min((c for c in (E.build(setup, scores, t, kib, 0.) for t in E.R.GAMA_TREES) if c),
                       key=lambda c: (c['structure'].est_fpr, c['trees']))
            for name, spec, family in specs:
                for seed in range(seeds):
                    stream = None
                    for kind, method in VARIANTS:
                        if (name, seed, method) in done:
                            continue
                        t0 = time.perf_counter()
                        if stream is None:
                            stream = E.stream_for(setup, name, spec, family, seed, queries, gama['structure'])
                            n = len(stream) // 4
                            setup.h1q[stream].astype(np.uint64).tofile(tmp / 'stream.u64')
                        p = subprocess.run([str(DRIVER), kind, str(kib * 1024), str(tmp / 'pos.u64'), str(tmp / 'stream.u64'),
                                            str(n), str(BREAK_EVEN)], capture_output=True, text=True)
                        rec = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, method=method)
                        if p.returncode != 0:
                            rec.update(error=(p.stderr or p.stdout)[-500:])
                        else:
                            rec.update(json.loads(p.stdout.strip().splitlines()[-1]), evaluation_queries=len(stream) - n)
                        rec['seconds'] = time.perf_counter() - t0
                        obj['rows'].append(rec)
                        dest.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
                        print(ds, kib, name, seed, method, {k: rec.get(k) for k in ('fp_tail', 'rbits', 'size_bytes', 'infeasible', 'rented', 'error')},
                              f"{rec['seconds']:.1f}s", flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets')
    a = p.parse_args()
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E.BUDGETS[a.dataset])

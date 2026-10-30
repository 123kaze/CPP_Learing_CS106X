"""Round 6: RA6 (option D) on the round-5 streams; baselines are reused from round 5.

Gama, FastPLBF48, Gama(original), Gama+10%, LearnGrid, RA4 and fp_oracle are deterministic on
identical streams and come from round5_dp/results/rows_*.csv; this script adds RA6 (top 5) and
the sensitivity variants RA6-top3 / RA6-top10, all seeds, same unified columns.
usage: run6.py --dataset <ds> [--budgets ...] [--tag main|holdout]
"""
import argparse
import csv
import resource
import sys
import time
from pathlib import Path
import numpy as np
import ra6

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'round5_dp' / 'src'))
import run5  # noqa: E402  (column list, helpers)

E5, RA = ra6.E5, ra6.RA
VARIANTS = (('RA6', 5), ('RA6-top3', 3), ('RA6-top10', 10))


def run(ds, budgets, queries, seeds, tag):
    setup, scores, safe = E5.load(ds)
    commit, hw = run5.env_info()
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
        for name, spec in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                start = time.perf_counter()
                base = E5.base_stream(setup, name, spec, seed, queries)
                n = len(base) // 4
                learn, base_tail = base[:n], base[n:]
                ts = time.perf_counter()
                lm = RA.ra4.summarize(learn, True)
                lm_s = time.perf_counter() - ts
                rows = []
                zipf_s, pool = run5.parse_workload(name)
                multi = ra6.select6_multi(setup, scores, lm, kib, len(base_tail), ks=tuple(k for _, k in VARIANTS))
                for vname, k in VARIANTS:
                    c, info = multi[k]
                    tail = E5.tail_for(c, name, base_tail, seed)
                    r = E5.evaluate(c, tail, setup, safe)
                    st = c['structure']
                    assert st.used_bytes <= kib * 1024
                    rows.append(dict(dataset=ds, budget_kib=kib, workload=name, zipf_s=zipf_s, pool=pool, seed=seed,
                                     method=vname, allocator='FastPLBF_M DP N=1000 k=5', trees=c['trees'],
                                     cache_reserved_bytes=c['cache_reserved_bytes'], cache_alloc_bytes=c['cache_bytes'],
                                     model_bytes=st.model_bytes, bf_bytes=st.filter_bytes, metadata_bytes=st.metadata_bytes,
                                     overhead_bytes=st.array_overhead_bytes, total_bytes=st.used_bytes, fp_tail=r['fp'],
                                     fpr_tail=r['fp'] / len(tail), fp_oracle='', pred_fp=info['predicted_fp'],
                                     cache_hit_rate=round(r.get('cache_hit_rate', 0.), 6), t_train_s='', t_score_s='',
                                     t_select_s=round(info['select_seconds'] + lm_s, 4), t_build_s=0,
                                     learn_state_bytes=lm.state_bytes,
                                     peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                     query_ns_mean='', query_ns_p50='', query_ns_p99='', backend_calls='',
                                     e2e_ms_mean='', e2e_ms_p99='', code_commit=commit, hardware=hw))
                new = not dest.exists()
                with dest.open('a', encoding='utf-8', newline='') as fh:
                    w = csv.DictWriter(fh, fieldnames=run5.COLS)
                    if new:
                        w.writeheader()
                    w.writerows(rows)
                print(f'{ds} {kib}KiB {name} s{seed} {time.perf_counter()-start:.1f}s '
                      + ' '.join(f"{r['method']}={r['fp_tail']}" for r in rows), flush=True)
        print(f'COMPLETE {ds}/{kib}', flush=True)
        E5._TREE.clear()
        E5.R._GSETUPS.clear()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets')
    p.add_argument('--queries', type=int, default=10_000_000)
    p.add_argument('--seeds', type=int, default=5)
    p.add_argument('--tag', default='main')
    a = p.parse_args()
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E5.BUDGETS[a.dataset],
        a.queries, a.seeds, a.tag)

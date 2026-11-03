"""Round 10: RA6 with the index-free 64-bit fingerprint cache, on round 6's main-table cases.

Frozen RA6 (round6_bucket/src/ra6.py, top 5) is run unchanged; only the cache module the engine
uses is replaced (engine5.K -> cache_fp), so the candidate table, the slot count of every cache
size, the bucket-load prediction and the replay all see the fingerprint layout.  Same streams,
datasets, budgets, workloads and seeds as round6_bucket/results/main; Gama and the index-based
RA6 rows are read from there (Gama has no cache and is unaffected).
Per case also: member_hits_final = members the final cache state would answer "cached negative"
(measured false negatives over all members), and the union bound occupied * 2^-64 per member query.
usage: run10.py --dataset <ds> [--budgets ...] [--tag main]   -> results/<tag>/rows_<ds>_<kib>.csv
"""
import argparse
import csv
import sys
import time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'round6_bucket' / 'src'))
import cache_fp as F  # noqa: E402
import ra6  # noqa: E402  (frozen round 6)

E5, RA = ra6.E5, ra6.RA
E5.K = F            # the only change: the engine's cache module
C5 = F.C5
COLS = ['dataset', 'budget_kib', 'workload', 'seed', 'method', 'trees', 'frac', 'cache_alloc_bytes', 'slots',
        'total_bytes', 'fp_tail', 'tail_len', 'pred_fp', 'hits', 'inserts', 'evictions', 'occupied',
        'member_hits_final', 'fn_bound_per_query', 't_select_s', 'case_s']


def run(ds, budgets, queries, seeds, tag='main'):
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
        for name, spec in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                start = time.perf_counter()
                base = E5.base_stream(setup, name, spec, seed, queries)
                n = len(base) // 4
                learn, base_tail = base[:n], base[n:]
                lm = RA.ra4.summarize(learn, True)
                c, info = ra6.select6(setup, scores, lm, kib, len(base_tail))
                tail = E5.tail_for(c, name, base_tail, seed)
                st = c['structure']
                assert st.used_bytes <= kib * 1024
                if c['cache_bytes'] and E5.K is C5:      # --cache index: regression check against round 6
                    r = C5.simulate(tail, setup.h1q, safe, st.fp_static, c['cache_bytes'], E5.PREFIX, E5.WAYS)
                    r['member_hits_final'] = -1
                elif c['cache_bytes']:
                    r = F.simulate(tail, setup.h1q, None, st.fp_static, c['cache_bytes'],
                                   member_hashes=setup.member_hashes)
                    assert r['allocated_bytes'] == c['cache_bytes']
                else:
                    r = dict(fp=int(st.fp_static[tail].sum()), hits=0, inserts=0, evictions=0, occupied=0,
                             slots=0, member_hits_final=0)
                row = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, method='RA6-fp64' if E5.K is F else 'RA6', trees=c['trees'],
                           frac=info['frac'], cache_alloc_bytes=c['cache_bytes'], slots=r['slots'], total_bytes=st.used_bytes,
                           fp_tail=r['fp'], tail_len=len(tail), pred_fp=info['predicted_fp'], hits=r['hits'],
                           inserts=r['inserts'], evictions=r['evictions'], occupied=r['occupied'],
                           member_hits_final=r['member_hits_final'], fn_bound_per_query=r['occupied'] * 2.0 ** -64,
                           t_select_s=round(info['select_seconds'], 4), case_s=round(time.perf_counter() - start, 2))
                new = not dest.exists()
                with dest.open('a', encoding='utf-8', newline='') as fh:
                    w = csv.DictWriter(fh, fieldnames=COLS)
                    if new:
                        w.writeheader()
                    w.writerow(row)
                print(f"{ds} {kib}KiB {name} s{seed} {row['case_s']}s {row['method']}={r['fp']} "
                      f"trees={c['trees']} frac={info['frac']} FN={r['member_hits_final']}", flush=True)
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
    p.add_argument('--cache', choices=('fp64', 'index'), default='fp64',
                   help='index = frozen cache5 with the member index (must reproduce round 6)')
    a = p.parse_args()
    if a.cache == 'index':
        E5.K = C5
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E5.BUDGETS[a.dataset],
        a.queries, a.seeds, a.tag)

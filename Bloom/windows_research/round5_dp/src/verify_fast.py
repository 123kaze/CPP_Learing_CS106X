"""Check that ra5fast.select_fast picks the same (trees, cache fraction) as ra5.select on every
round-5 case (dataset, budget, workload, seed); the chosen RA4 config is read from rows_*.csv.
usage: verify_fast.py <dataset> <budget_kib>   -> results/verify_fast/<ds>_<kib>.json
"""
import csv
import json
import sys
from pathlib import Path
import engine5 as E5
import ra5 as RA
import ra5fast as RF

ROOT = Path(__file__).resolve().parents[1]


def main(ds, kib):
    setup, scores, safe = E5.load(ds)
    rows = [r for r in csv.DictReader(open(ROOT / 'results' / f'rows_{ds}_{kib}.csv', encoding='utf-8')) if r['method'] == 'RA4']
    specs = dict(E5.workload_specs(len(setup.h1q))) if not ds.endswith('_flow') else {'真实轨迹': None}
    out, diff = [], 0
    for r in rows:
        seed = int(r['seed'])
        base = E5.base_stream(setup, r['workload'], specs[r['workload']], seed)
        n = len(base) // 4
        lm = RA.ra4.summarize(base[:n], True)
        c, info = RF.select_fast(setup, scores, lm, kib, len(base) - n, RA.Config(new_mix=0.))
        same = int(r['trees']) == info['trees'] and int(r['cache_alloc_bytes']) == c['cache_bytes']
        diff += not same
        out.append(dict(workload=r['workload'], seed=seed, ra4=(int(r['trees']), int(r['cache_alloc_bytes'])),
                        fast=(info['trees'], c['cache_bytes']), same=same, fast_select_s=info['select_seconds']))
    dest = ROOT / 'results' / 'verify_fast'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f'{ds}_{kib}.json').write_text(json.dumps(dict(cases=len(out), different=diff, rows=out), ensure_ascii=False, indent=1))
    print(ds, kib, 'cases', len(out), 'different', diff, flush=True)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]))

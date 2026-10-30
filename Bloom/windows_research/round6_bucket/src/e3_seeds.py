"""E3 for the frozen RA6 predictor on data that was never used to design option D.

Synthetic: seeds 1-4 of every round-5 synthetic setting (option D was developed on seed 0).
For each case RA4's candidate table is recomputed, its top 10 are built, measured on the
evaluation segment and re-predicted from the actual bucket load.  Probe replay is excluded
(its tail depends on the structure and the learning period has no replays).
usage: e3_seeds.py <dataset> <budget_kib>  -> results/e3_seeds/<ds>_<kib>.json
"""
import json
import sys
from pathlib import Path
import ra6

ROOT = Path(__file__).resolve().parents[1]
E5, RA = ra6.E5, ra6.RA
TOP = 10


def main(ds, kib, seeds=(1, 2, 3, 4)):
    setup, scores, safe = E5.load(ds)
    specs = E5.workload_specs(len(setup.h1q))
    dest = ROOT / 'results' / 'e3_seeds'
    dest.mkdir(parents=True, exist_ok=True)
    f = dest / f'{ds}_{kib}.json'
    out = json.loads(f.read_text(encoding='utf-8')) if f.exists() else []
    done = {(r['workload'], r['seed']) for r in out}
    cfg = RA.Config(new_mix=0.)
    for name, spec in specs:
        if name == E5.PROBE:
            continue
        for seed in seeds:
            if (name, seed) in done:
                continue
            base = E5.base_stream(setup, name, spec, seed)
            n = len(base) // 4
            tail = base[n:]
            H = len(tail)
            lm = RA.ra4.summarize(base[:n], True)
            table = RA.candidate_table(setup, scores, lm, kib, H, cfg)
            short = sorted(table, key=lambda r: (r['pred'], r['trees'], r['frac']))[:TOP]
            rows = []
            for row in short:
                c = E5.build(setup, scores, row['trees'], kib, row['frac'], weights=row['weights'],
                             cache_bytes=row['cache_bytes'], slots=row['slots'])
                pred_d = ra6.bucket_prediction(setup, lm, E5.tree(setup, scores, row['trees']), c, H, row['seg_fpr_pred'])
                meas = E5.evaluate(c, tail, setup, safe)['fp']
                rows.append([row['trees'], row['frac'], row['pred'], pred_d, meas])
            out.append(dict(workload=name, seed=seed, rank_rows=rows))
            f.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
            print(ds, kib, name, seed, flush=True)
        E5.R._GSETUPS.clear()
    E5._TREE.clear()


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]))

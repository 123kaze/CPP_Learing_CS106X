"""E3 on the MAWI 2024 holdout (never used for design): every RA4 candidate was built and measured
in the one-shot holdout run (round5_methods/e3_*.jsonl); here each is re-predicted from the actual
bucket load (RA6's predictor).  Run through holdout6.py so that mawi2024_flow is registered.
-> results/holdout/e3_holdout.json
"""
import json
from pathlib import Path
import ra6

ROOT = Path(__file__).resolve().parents[1]
E5, RA = ra6.E5, ra6.RA


def main():
    ds = 'mawi2024_flow'
    setup, scores, safe = E5.load(ds)
    out = []
    for f in sorted((ROOT / 'results' / 'holdout' / 'round5_methods').glob('e3_mawi2024_flow_*.jsonl')):
        kib = int(f.stem.rsplit('_', 1)[1])
        for line in f.read_text(encoding='utf-8').splitlines():
            rec = json.loads(line)
            base = E5.base_stream(setup, '真实轨迹', None, 0)
            n = len(base) // 4
            H = len(base) - n
            lm = RA.ra4.summarize(base[:n], True)
            table = {(r['trees'], r['frac']): r for r in RA.candidate_table(setup, scores, lm, kib, H, RA.Config(new_mix=0.))}
            rows = []
            for c in rec['candidates']:
                row = table[c['trees'], c['frac']]
                assert abs(row['pred'] - c['pred']) <= 1e-9 * max(1., c['pred'])
                built = E5.build(setup, scores, row['trees'], kib, row['frac'], weights=row['weights'],
                                 cache_bytes=row['cache_bytes'], slots=row['slots'])
                pred_d = ra6.bucket_prediction(setup, lm, E5.tree(setup, scores, row['trees']), built, H, row['seg_fpr_pred'])
                rows.append([row['trees'], row['frac'], row['pred'], pred_d, c['measured']])
            out.append(dict(budget_kib=kib, rows=rows))
            print(ds, kib, len(rows), flush=True)
    (ROOT / 'results' / 'holdout' / 'e3_holdout.json').write_text(json.dumps(out), encoding='utf-8')


if __name__ == '__main__':
    main()

"""Scores of a prefix of the shared 200-tree model for the original PLBF code (FastPLBF repo).

members.csv / train_neg.csv (= neg_val) / query.csv (= neg_test pool, stream order),
columns key,label,score with score = sigmoid(raw); model.json = executable model bytes.
Usage: export_scores.py <dataset> <trees,...>.  Run with the project env (Bloom/.condaenv).
"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'windows_research' / 'round3_ra_plbf' / 'src'))
import ra_plbf as RA  # noqa: E402

def export(ds, TREES):
    out = HERE / 'data' / ds / f't{TREES}'
    out.mkdir(parents=True, exist_ok=True)
    setup, scores, _ = RA.E.load(ds)
    gs = RA.tree_setup(setup, scores, TREES)
    sig = lambda s: 1 / (1 + np.exp(-s))  # noqa: E731
    sp = setup.split
    for name, keys, score, label in (('members', setup.ids[setup.y], gs.mem_score, 1),
                                     ('train_neg', setup.ids[sp['neg_val']], gs.val_score, 0),
                                     ('query', setup.q_ids, gs.q_score, 0)):
        pd.DataFrame(dict(key=keys.astype(str), label=label, score=sig(score))).to_csv(
            out / f'{name}.csv', index=False, float_format='%.17g')
    model_bytes = sum(a.nbytes for a in RA.R._MODEL_ARRAYS[setup.name, TREES].values())
    (out / 'model.json').write_text(json.dumps(dict(trees=TREES, model_bytes=int(model_bytes))))
    print(ds, 'members', int(setup.y.sum()), 'model bytes', model_bytes, flush=True)


if __name__ == '__main__':
    ds = sys.argv[1]
    for t in sys.argv[2].split(','):
        export(ds, int(t))

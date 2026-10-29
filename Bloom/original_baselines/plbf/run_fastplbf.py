"""Run FastPLBF_M from atsukisato/FastPLBF (commit 9491e7e) unchanged on exported scores.

Differs from its __main__ only in data plumbing: build on the validation negatives
instead of a random 30% split, query the whole test pool and keep per-key FP flags.
Usage: run_fastplbf.py <data dir> <budgets KiB,...> <out dir> [N] [k]
Run with Bloom/.condaenv_gama (bloom-filter, pandas, scikit-learn).
"""
import json
import os
import sys
import time
import numpy as np
import pandas as pd

REPO = os.environ['FASTPLBF_REPO']
sys.path.insert(0, os.path.join(REPO, 'src', 'PLBFs'))
from FastPLBF_M import FastPLBF_M  # noqa: E402

data, budgets, out = sys.argv[1], [int(x) for x in sys.argv[2].split(',')], sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
k = int(sys.argv[5]) if len(sys.argv) > 5 else 5
os.makedirs(out, exist_ok=True)
members = pd.read_csv(os.path.join(data, 'members.csv'))
train_neg = pd.read_csv(os.path.join(data, 'train_neg.csv'))
query = pd.read_csv(os.path.join(data, 'query.csv'))
model_bytes = json.load(open(os.path.join(data, 'model.json')))['model_bytes']
pos_keys, pos_scores = list(members['key']), list(members['score'])
neg_scores = list(train_neg['score'])
q_keys, q_scores = list(query['key']), list(query['score'])

for kib in budgets:
    M = float((kib * 1024 - model_bytes) * 8)   # backup BF bits: budget minus the model
    rec = dict(budget_kib=kib, model_bytes=model_bytes, M_bits=M, N=N, k=k)
    if M <= 0:
        rec['infeasible'] = 'model alone exceeds the budget'
    else:
        t0 = time.time()
        plbf = FastPLBF_M(pos_keys, pos_scores, neg_scores, M, N, k)
        rec['construction_seconds'] = time.time() - t0
        assert all(plbf.contains(key, s) for key, s in zip(pos_keys, pos_scores)), 'false negative'
        flags = np.fromiter((plbf.contains(key, s) for key, s in zip(q_keys, q_scores)), np.bool_, len(q_keys))
        np.save(os.path.join(out, f'fp_{kib}.npy'), flags)
        rec.update(memory_usage_of_backup_bf=float(plbf.memory_usage_of_backup_bf),
                   query_fp=int(flags.sum()), query_fpr=float(flags.mean()), member_false_negatives=0)
    json.dump(rec, open(os.path.join(out, f'plbf_{kib}.json'), 'w'), indent=2)
    print(json.dumps(rec), flush=True)

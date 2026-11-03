"""Where does RA6's systematic over-prediction come from?  (diagnostic, method unchanged)

RA6's prediction for a built structure (ra6.bucket_prediction) has two parts:
  seen   keys queried in the learning period: per-bucket Che with Good-Turing rates (Eq. 7);
  unseen keys never queried in the learning period: G_i = H * N1/L * h_i tail queries per segment,
         each charged as a miss with the segment's FPR (Eq. 5), i.e. assumed never cached.
For RA6's pick in every E3 case (same cases as eq7_offline.py), the structure is rebuilt, the tail
is replayed with per-key miss counts, and the measured misses are split the same way.  For the
unseen keys three measured quantities separate the possible causes:
  q_fp   tail queries to unseen keys that are static FPs of the structure (= misses without a cache);
  d_fp   distinct such keys (lower bound on their misses with a cache: the first query always misses);
  miss   their actual misses with the cache.
pred_new vs q_fp tests G's volume and spread over segments; q_fp vs miss is what the cache saves.

usage: bias_split.py seeds <dataset> <kib>   -> results/split_<ds>_<kib>.json
       holdout6.py run bias_split.py holdout -> results/split_holdout_mawi2024_flow.json
"""
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eq7_offline as Q  # noqa: E402

ROOT, R6, E5, RA, ra6 = Q.ROOT, Q.R6, Q.E5, Q.RA, Q.ra6
K = 5


def split(setup, scores, safe, lm, kib, H, tail, t, f):
    table = {(r['trees'], r['frac']): r for r in RA.candidate_table(setup, scores, lm, kib, H, RA.Config(new_mix=0.))}
    row = table[t, f]
    c = E5.build(setup, scores, t, kib, f, weights=row['weights'], cache_bytes=row['cache_bytes'], slots=row['slots'])
    td = E5.tree(setup, scores, t)
    st = c['structure']
    total = ra6.bucket_prediction(setup, lm, td, c, H, row['seg_fpr_pred'])
    G = H * lm.N1 / lm.L * td.h
    pred_new = float((row['seg_fpr_pred'] * G).sum())
    r = E5.evaluate(c, tail, setup, safe, per_key=True)
    miss = r['miss']
    seen = np.zeros(len(setup.h1q), bool)
    seen[lm.keys] = True
    fp = st.fp_static
    qn = np.bincount(tail, minlength=len(seen))
    new_fp = (~seen) & fp
    return dict(trees=t, frac=f, cache_bytes=int(c['cache_bytes']),
                pred_total=total, pred_seen=total - pred_new, pred_new=pred_new,
                meas_total=int(miss.sum()), meas_seen=int(miss[seen].sum()), meas_new=int(miss[~seen].sum()),
                new_q_fp=int(qn[new_fp].sum()), new_d_fp=int((new_fp & (qn > 0)).sum()),
                # structure-free volume of unseen-key traffic: Good-Turing estimate vs actual
                G_total=float(H * lm.N1 / lm.L), new_q=int(qn[~seen].sum()), new_d=int(((~seen) & (qn > 0)).sum()),
                tail=int(H))


def pick(rows):
    """RA6's choice: first minimum of the original prediction inside RA4's top K."""
    top = rows[:K]
    i = min(range(len(top)), key=lambda j: top[j][3])
    return top[i][0], top[i][1]


def seeds(ds, kib):
    setup, scores, safe = E5.load(ds)
    specs = dict(E5.workload_specs(len(setup.h1q)))
    src = json.loads((ROOT / 'results' / f'seeds_{ds}_{kib}.json').read_text(encoding='utf-8'))
    dest = ROOT / 'results' / f'split_{ds}_{kib}.json'
    out = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else []
    done = {(r['workload'], r['seed']) for r in out}
    for rec in src:
        if (rec['workload'], rec['seed']) in done:
            continue
        base = E5.base_stream(setup, rec['workload'], specs[rec['workload']], rec['seed'])
        n = len(base) // 4
        lm = RA.ra4.summarize(base[:n], True)
        t, f = pick(rec['rows'])
        s = split(setup, scores, safe, lm, kib, len(base) - n, base[n:], t, f)
        meas = next(x[5] for x in rec['rows'] if x[0] == t and x[1] == f)
        assert s['meas_total'] == meas, (s['meas_total'], meas)
        out.append(dict(workload=rec['workload'], seed=rec['seed'], best10=min(x[5] for x in rec['rows']), **s))
        dest.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
        print(ds, kib, rec['workload'], rec['seed'], flush=True)


def holdout():
    ds = 'mawi2024_flow'
    setup, scores, safe = E5.load(ds)
    src = json.loads((ROOT / 'results' / 'holdout_mawi2024_flow.json').read_text())
    base = E5.base_stream(setup, '真实轨迹', None, 0)
    n = len(base) // 4
    lm = RA.ra4.summarize(base[:n], True)
    out = []
    for rec in src:
        rows = sorted(rec['rows'], key=lambda x: (x[2], x[0], x[1]))
        t, f = pick(rows)
        s = split(setup, scores, safe, lm, rec['budget_kib'], len(base) - n, base[n:], t, f)
        assert s['meas_total'] == next(x[5] for x in rows if x[0] == t and x[1] == f)
        out.append(dict(budget_kib=rec['budget_kib'], **s))
        print(ds, rec['budget_kib'], flush=True)
    (ROOT / 'results' / 'split_holdout_mawi2024_flow.json').write_text(json.dumps(out), encoding='utf-8')


if __name__ == '__main__':
    if sys.argv[1] == 'seeds':
        seeds(sys.argv[2], int(sys.argv[3]))
    else:
        holdout()

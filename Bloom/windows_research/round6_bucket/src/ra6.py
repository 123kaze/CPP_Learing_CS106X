"""Round 6 (option D): RA4 shortlist + prediction from the actual bucket load.

1. ra5.candidate_table (frozen round 5) ranks every (trees, cache fraction) candidate by RA4's
   prediction;
2. the TOPK best are built (FastPLBF DP with RA4's weights, Bloom insert);
3. for each, the learning-period keys that are FPs of that structure are hashed with cache5's
   bucket function and every bucket gets its own Che characteristic time from its own keys'
   Good-Turing rates (WAYS slots per bucket); unseen-key tail queries keep the expected
   treatment (eps_i * G_i, NEW_MIX = 0), their occupancy spread evenly over buckets;
4. the candidate with the smallest bucket-load prediction is deployed (already built).
No learning trace is needed: only the per-key learning counts that RA4 already keeps.
Without repeats every candidate's prediction is RA4's, so the choice is RA4's (= Gama).
"""
import sys
import time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'round5_dp' / 'src'))
import engine5 as E5  # noqa: E402  (frozen round 5)
import ra5 as RA  # noqa: E402

TOPK = 5
WAYS = E5.WAYS


def buckets_of(h, B, P=E5.PREFIX):
    Q = min(P, 32)
    x = np.asarray(h, np.uint64) >> np.uint64(64 - Q)
    return ((x * np.uint64(B)) >> np.uint64(Q)).astype(np.int64)


def bucket_che(lam, b, B, H, g_new, iters=60):
    """Tail misses of keys with rates lam in buckets b: per-bucket T_b with
    sum_k (1 - exp(-lam_k * min(T,H))) + g_new * min(T,H) = WAYS."""
    lo = np.zeros(B)
    hi = np.full(B, np.log(1e3 * H))
    cnt = np.bincount(b, minlength=B)
    for _ in range(iters):
        mid = (lo + hi) / 2
        T = np.minimum(np.exp(mid), H)
        occ = np.bincount(b, 1 - np.exp(-lam * T[b]), minlength=B) + g_new * T
        over = occ > WAYS
        hi = np.where(over, mid, hi)
        lo = np.where(over, lo, mid)
    T = np.exp(lo)
    T = np.where((cnt <= WAYS) & (g_new * H <= WAYS - cnt), 1e3 * H, T)
    a = 1 - np.exp(-lam * H)
    return float((a + np.maximum(0, lam * H - a) * np.exp(-lam * T[b])).sum())


def bucket_prediction(setup, lm, td, c, H, seg_fpr):
    """seg_fpr: the candidate's per-segment FPR used by RA4's own prediction (unseen-key part),
    so that without repeats every prediction equals RA4's exactly."""
    st = c['structure']
    fpk = st.fp_static[lm.keys]
    lam = lm.rate[fpk]
    G = H * lm.N1 / lm.L * td.h
    new_miss = float((seg_fpr * G).sum())
    if c['cache_bytes'] == 0:
        return float((lam * H).sum()) + new_miss
    B = c['slots'] // WAYS
    b = buckets_of(setup.h1q[lm.keys[fpk]], B)
    return bucket_che(lam, b, B, H, new_miss / H / B) + new_miss


def select6_multi(setup, scores, lm, kib, H, ks=(3, 5, 10), cfg=None):
    """One candidate table and one set of built structures for several shortlist sizes."""
    cfg = cfg or RA.Config(new_mix=0.)
    t0 = time.perf_counter()
    table = RA.candidate_table(setup, scores, lm, kib, H, cfg)
    t_table = time.perf_counter() - t0
    short = sorted(table, key=lambda r: (r['pred'], r['trees'], r['frac']))[:max(ks)]
    built = []
    for rank, row in enumerate(short):
        tb = time.perf_counter()
        c = E5.build(setup, scores, row['trees'], kib, row['frac'], weights=row['weights'],
                     cache_bytes=row['cache_bytes'], slots=row['slots'])
        pred = bucket_prediction(setup, lm, E5.tree(setup, scores, row['trees']), c, H, row['seg_fpr_pred'])
        built.append(((pred, rank), c, row, time.perf_counter() - tb))
    out = {}
    for k in ks:
        (pred, rank), c, row, _ = min(built[:k], key=lambda x: x[0])
        out[k] = (c, dict(trees=row['trees'], frac=row['frac'], predicted_fp=pred, ra4_rank=rank,
                          select_seconds=t_table + sum(x[3] for x in built[:k]), build_seconds=0.,
                          candidates=len(table), built=min(k, len(built))))
    return out


def select6(setup, scores, lm, kib, H, cfg=None, topk=TOPK):
    return select6_multi(setup, scores, lm, kib, H, ks=(topk,), cfg=cfg)[topk]

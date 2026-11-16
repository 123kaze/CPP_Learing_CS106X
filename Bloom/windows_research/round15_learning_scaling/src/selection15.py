"""Exact round6/E5 selection paths with inclusive learning preprocessing timers.

Frozen DP/BF/CLOCK helpers are imported, not rewritten. Replay retains incumbent
cutoffs and the exact no-cache weighted-count shortcut. No training is timed.
"""
import os
for v in ('OMP_NUM_THREADS', 'NUMBA_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[v] = '1'
import sys
import time
import numpy as np
from common15 import WR, KIB, CHUNK, array_hash
sys.path.insert(0, str(WR / 'round6_bucket/src'))
import e5_scaling as OLD
E5, RA, R6, K = OLD.E5, OLD.RA, OLD.ra6, OLD.K


def descriptors(setup, scores):
    out = []
    for t in E5.TREES:
        td = E5.tree(setup, scores, t)
        for frac in E5.FRACS:
            cb, slots = E5.cache_alloc(KIB * 1024, frac)
            if td.fixed + cb < KIB * 1024:
                out.append((t, frac, cb, slots))
    return out


def prepare_shared(setup, scores):
    # Segment arrays depend on fixed model/data only, not the learning period.
    return {t: E5.tree(setup, scores, t) for t in E5.TREES}


def select_ra(setup, scores, tds, learn):
    start = time.perf_counter()
    lm = RA.ra4.summarize(learn, True)
    count_done = time.perf_counter()
    H = 3 * len(learn)
    table = RA.candidate_table(setup, scores, lm, KIB, H, RA.Config(new_mix=0.))
    table_done = time.perf_counter()
    short = sorted(table, key=lambda row: (row['pred'], row['trees'], row['frac']))[:R6.TOPK]
    best = None
    for rank, row in enumerate(short):
        td = tds[row['trees']]
        bits, flags, _ = OLD.dp_bf(setup, td, KIB, row['cache_bytes'], weights=row['weights'], query_idx=lm.keys)
        lam = lm.rate[flags]
        G = H * lm.N1 / lm.L * td.h
        new_miss = float((row['seg_fpr_pred'] * G).sum())
        if row['cache_bytes'] == 0:
            pred = float((lam * H).sum()) + new_miss
        else:
            B = row['slots'] // R6.WAYS
            pred = R6.bucket_che(lam, R6.buckets_of(setup.h1q[lm.keys[flags]], B), B, H, new_miss / H / B) + new_miss
        if best is None or (pred, rank) < best[0]:
            best = ((pred, rank), row, flags)
    end = time.perf_counter()
    (_, rank), chosen, flags = best
    meta = dict(selection_s=end-start, count_s=count_done-start, local_map_s=0.,
                predict_table_s=table_done-count_done, build_refine_s=end-table_done,
                candidate_build_s=0., replay_s=0., candidates=len(table), built=len(short),
                distinct_keys=len(lm.keys), learning_state_bytes=lm.keys.nbytes + lm.counts.nbytes + lm.rate.nbytes,
                count_state_bytes=lm.keys.nbytes + lm.counts.nbytes, candidate_query_visits=0,
                ra4_rank=rank, predicted_fp=best[0][0])
    return meta, chosen, lm.keys, flags, lm


def select_replay(setup, scores, tds, safe, learn):
    start = time.perf_counter()
    keys, freq = np.unique(learn, return_counts=True)
    count_done = time.perf_counter()
    # Same local-key representation as E5, with bounded temporary allocation.
    local = np.empty(len(learn), np.int64)
    for lo in range(0, len(learn), CHUNK):
        local[lo:lo+CHUNK] = np.searchsorted(keys, learn[lo:lo+CHUNK])
    hashes, lengths = setup.h1q[keys], safe[keys]
    map_done = time.perf_counter()
    order = []
    for t, frac, cb, slots in descriptors(setup, scores):
        bits, flags, e = OLD.dp_bf(setup, tds[t], KIB, cb, query_idx=keys)
        del bits
        order.append((e, t, frac, cb, slots, flags))
    order.sort(key=lambda r: r[:3])
    build_done = time.perf_counter()
    best = None
    records = []
    for e, t, frac, cb, slots, flags in order:
        limit = best[0] if best else 2**62
        before = time.perf_counter()
        if cb == 0:
            fp, cutoff, processed = int(freq[flags].sum()), False, 0
        else:
            measured = K.simulate(local, hashes, lengths, flags, cb, E5.PREFIX, E5.WAYS, limit=limit)
            fp, cutoff, processed = measured['fp'], bool(measured['cutoff']), measured['processed']
        records.append(dict(trees=t, frac=frac, cache_bytes=cb, fp=fp, cutoff=cutoff,
                            processed=processed, seconds=time.perf_counter()-before))
        key = (fp, e, t, frac)
        if not cutoff and (best is None or key < best):
            best = key
            chosen = dict(trees=t, frac=frac, cache_bytes=cb, slots=slots)
            chosen_flags = flags
    end = time.perf_counter()
    meta = dict(selection_s=end-start, count_s=count_done-start, local_map_s=map_done-count_done,
                predict_table_s=0., build_refine_s=0., candidate_build_s=build_done-map_done,
                replay_s=end-build_done, candidates=len(order), built=len(order),
                distinct_keys=len(keys), learning_state_bytes=local.nbytes + keys.nbytes + freq.nbytes + hashes.nbytes + lengths.nbytes,
                count_state_bytes=keys.nbytes + freq.nbytes, candidate_query_visits=sum(r['processed'] for r in records),
                cached_candidates=sum(r['cache_bytes']>0 for r in records),
                cutoff_candidates=sum(r['cutoff'] for r in records), learning_fp=best[0], replay_records=records)
    return meta, chosen, keys, chosen_flags, (local, hashes, lengths, order, freq)


def verify_choice(method, setup, scores, safe, learn, choice, keys, flags, aux, pilot):
    # Full member acceptance and physical-budget assertions live in frozen E5.build.
    c = E5.build(setup, scores, choice['trees'], KIB, choice['frac'], weights=choice.get('weights'),
                 cache_bytes=choice['cache_bytes'], slots=choice['slots'])
    assert c['structure'].used_bytes <= KIB * 1024
    assert np.array_equal(c['structure'].fp_static[keys], flags), 'local DP/BF disagrees with frozen full-pool build'
    out = dict(trees=choice['trees'], frac=choice['frac'], cache_bytes=choice['cache_bytes'],
               used_bytes=c['structure'].used_bytes, member_false_negatives=0,
               full_static_flags_sha256=array_hash(c['structure'].fp_static), local_flags_sha256=array_hash(flags),
               keys_sha256=array_hash(keys), verified_full_build=True)
    if method == 'ra6':
        if pilot:
            canonical, info = R6.select6(setup, scores, aux, KIB, 3*len(learn))
            assert (canonical['trees'], canonical['frac']) == (c['trees'], c['frac'])
            assert np.array_equal(canonical['structure'].fp_static, c['structure'].fp_static)
            out['canonical_ra6_check'] = True
    else:
        local, hashes, lengths, order, freq = aux
        got = (int(freq[flags].sum()) if c['cache_bytes'] == 0 else
               K.simulate(local, hashes, lengths, flags, c['cache_bytes'], E5.PREFIX, E5.WAYS)['fp'])
        out['learning_fp_check'] = got
        if pilot:
            # Independent, no-cutoff winner check plus local/full cache mapping check.
            best = None
            for e, t, f, cb, _, mask in order:
                v = int(freq[mask].sum()) if cb == 0 else K.simulate(local, hashes, lengths, mask, cb, E5.PREFIX, E5.WAYS)['fp']
                key = (v, e, t, f)
                if best is None or key < best: best = key
            assert (best[0], best[2], best[3]) == (got, c['trees'], c['frac'])
            full = E5.evaluate(c, learn, setup, safe)['fp']
            assert full == got
            out.update(no_cutoff_grid_check=True, full_pool_replay_check=True)
    return out

"""Round7 worker copied for paired loop/leaf timing; frozen selection/query logic unchanged."""
import argparse
import hashlib
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'round7_original_e2e/src'))
sys.path.insert(0, str(HERE.parents[1] / 'round13_complete/src'))
from leaf_scores import prefix_raw_scores


def digest_array(a):
    return hashlib.sha256(a.view('uint8')).hexdigest()

import shared as S
import csv
import sys
import time
import traceback
from types import SimpleNamespace
import numpy as np
import lightgbm as lgb

sys.path.insert(0, str(S.ROOT.parent / 'round6_bucket' / 'src'))
import e789 as J
from end_to_end import model_arrays
E5, C, R = J.E5, J.C, J.R


def warm_jit():
    t0 = time.perf_counter()
    h = np.array([1, 2], np.uint64)
    reg = np.zeros(2, np.int32)
    off, m, k = np.array([0, 64]), np.array([64]), np.array([1])
    bits = np.zeros(8, np.uint8)
    R.packed_build(h, reg, off, m, k, bits)
    R.packed_query(h, reg, np.array([int(C.BF)], np.uint8), off, m, k, bits)
    J.D.allocate(np.ones(J.D.N_SEG, np.int64), np.ones(J.D.N_SEG), 8000.)
    x = object.__new__(J.Exe)
    x.model = (np.empty(0, np.int16), np.empty(0), np.empty(0, np.int16),
               np.empty(0, np.int16), np.array([0.]), np.array([-1], np.int16))
    x.raw_cuts = np.array([-np.inf, np.inf])
    x.reg_of_seg = np.zeros(1, np.int64)
    x.kind, x.off, x.m, x.k, x.bits = np.array([int(C.PASS)]), off, m, k, bits
    x.cache_bytes = 1024
    x.spec = J.K.layout(1024)
    x.space = SimpleNamespace(X=np.zeros((2, 2), np.float32), h=h, member=np.zeros(2, np.bool_),
                              sorted_m=np.array([2 ** 63], np.uint64))
    x.run(np.array([0, 1]), 0, 2, 2, x.fresh_cache())
    J.scores_numba(x.space.X, np.array([0, 1]), *x.model)
    return time.perf_counter() - t0


def main(a):
    out = dict(method='RA6', dataset=a.dataset, budget_kib=a.budget, status='running',
               scoring=a.scoring, chunk_rows=a.chunk_rows, worker_sha256=S.digest(Path(__file__)),
               leaf_helper_sha256=S.digest(HERE.parents[1] / 'round13_complete/src/leaf_scores.py'))
    try:
        out['jit_setup_s'] = warm_jit()
        t = time.perf_counter()
        ids, y, X, features = C.load_dataset(a.dataset)
        sp = C.make_split(ids, y, a.dataset)
        folder, meta = S.fixture(a.dataset)
        learn = np.load(folder / 'learn.npy')
        tail = np.load(folder / 'tail.npy')
        assert np.array_equal(ids[y], np.load(folder / 'member_ids.npy'))
        assert np.array_equal(ids[sp['neg_test']], np.load(folder / 'query_ids.npy'))
        out['read_prepare_s'] = time.perf_counter() - t
        out['fixture'] = meta
        begin = time.perf_counter()
        train = sp['member_train'] | sp['neg_train']
        booster = lgb.train(dict(objective='binary', num_leaves=31, learning_rate=.1, num_threads=1,
                                  verbose=-1, seed=1, deterministic=True, force_col_wise=True),
                            lgb.Dataset(X[train], label=y[train], feature_name=features), num_boost_round=200)
        out['train_s'] = time.perf_counter() - begin
        print(f'TRAINED RA6 {a.dataset}: {out["train_s"]:.2f}s', flush=True)
        t = time.perf_counter()
        h = C.splitmix64(ids ^ np.uint64(C.H1_SALT))
        keys = np.unique(learn)
        local_sp = dict(sp)
        local_sp['neg_test'] = np.zeros(len(ids), np.bool_)
        local_sp['neg_test'][np.flatnonzero(sp['neg_test'])[keys]] = True
        setup = SimpleNamespace(name=a.dataset, ids=ids, y=y, split=local_sp, h1m=h[y],
                                h1q=h[sp['neg_test']][keys], q_ids=ids[local_sp['neg_test']])
        used = y | sp['neg_val'] | local_sp['neg_test']
        score_X = X[used]
        scores = {}
        if a.scoring == 'loop':
            for trees in E5.TREES:
                R._MODEL_ARRAYS[a.dataset, trees] = model_arrays(booster, trees)
                score = np.zeros(len(ids))
                score[used] = booster.predict(score_X, raw_score=True, num_iteration=trees, num_threads=1)
                scores[trees] = score
        else:
            prefixes = prefix_raw_scores(booster, score_X, E5.TREES, a.chunk_rows)
            for trees in E5.TREES:
                R._MODEL_ARRAYS[a.dataset, trees] = model_arrays(booster, trees)
                score = np.zeros(len(ids))
                score[used] = prefixes.pop(trees)
                scores[trees] = score
            del prefixes
        del score_X
        out['score_prepare_s'] = time.perf_counter() - t
        t = time.perf_counter()
        lm = J.RA.ra4.summarize(np.searchsorted(keys, learn).astype(np.int64), True)
        c, info = J.ra6.select6(setup, scores, lm, a.budget, len(tail))
        out['select_build_s'] = time.perf_counter() - t
        t = time.perf_counter()
        nm = int(y.sum())
        space = SimpleNamespace(sorted_m=np.sort(h[y]), nm=nm, nq=int(sp['neg_test'].sum()))
        exe = J.Exe(setup, scores, c, space)
        out['executable_prepare_s'] = time.perf_counter() - t
        out['train_to_ready_s'] = time.perf_counter() - begin
        # Exact-equivalence checks are outside ready and query timing.
        t = time.perf_counter()
        out['model_sha256'] = hashlib.sha256(booster.model_to_string().encode()).hexdigest()
        out['score_sha256'] = {str(trees): digest_array(score) for trees, score in scores.items()}
        out['bf_payload_sha256'] = digest_array(exe.bits)
        out['static_flags_sha256'] = digest_array(c['structure'].fp_static)
        out['executable_model_sha256'] = [digest_array(arr) for arr in exe.model]
        out['verification_hash_s'] = time.perf_counter() - t
        t = time.perf_counter()
        space.X = np.ascontiguousarray(np.vstack([X[y], X[sp['neg_test']]]))
        space.h = np.concatenate([h[y], h[sp['neg_test']]])
        space.member = np.concatenate([np.ones(nm, np.bool_), np.zeros(space.nq, np.bool_)])
        out['query_input_prepare_s'] = time.perf_counter() - t
        out.update(trees=c['trees'], cache_bytes=c['cache_bytes'], used_bytes=c['structure'].used_bytes,
                   member_index_bytes=space.sorted_m.nbytes, lightgbm=lgb.__version__, shortlist=info,
                   source_sha256=S.digest(S.ROOT.parent / 'round6_bucket' / 'src' / 'ra6.py'))
        assert out['used_bytes'] <= a.budget * 1024
        print(f'READY RA6 {a.dataset}: {out["train_to_ready_s"]:.2f}s trees={c["trees"]}', flush=True)
        t = time.perf_counter()
        idx = np.linspace(0, len(space.X) - 1, min(10000, len(space.X)), dtype=np.int64)
        raw = J.scores_numba(space.X, idx, *exe.model)
        assert np.max(np.abs(raw - booster.predict(space.X[idx], raw_score=True, num_iteration=c['trees'], num_threads=1))) < 1e-9
        members = np.arange(nm, dtype=np.int64)
        cnt, _ = exe.run(members, 0, nm, 1, exe.fresh_cache())
        assert cnt[2] == 0 and cnt[0] == nm
        out['member_false_negatives'] = int(cnt[2])
        qi = np.arange(space.nq, dtype=np.int64) + nm
        pool_cnt, pool_flags = exe.run(qi, 0, space.nq, 1, exe.fresh_cache())
        out['native_pool_flags_sha256'] = digest_array(pool_flags)
        out['native_pool_fp'] = int(pool_cnt[1])
        out['native_pool_queries'] = space.nq
        out['verification_s'] = time.perf_counter() - t
        out['queries'] = S.evaluate(lambda stream, lo, hi, data: exe.run(stream, lo, hi, 2, data)[0],
                                    exe.fresh_cache, a.dataset)
        ref_file = S.ROOT.parent / 'round6_bucket' / 'results' / 'main' / f'rows_{a.dataset}_{a.budget}.csv'
        ref = next(r for r in csv.DictReader(ref_file.open())
                   if r['method'] == 'RA6' and r['workload'] == meta['workload'] and r['seed'] == '0')
        got = (out['trees'], out['cache_bytes'], out['queries']['negative_tail']['fp'])
        want = (int(ref['trees']), int(ref['cache_alloc_bytes']), int(ref['fp_tail']))
        out['main_table_check'] = dict(actual=got, expected=want, equal=got == want)
        assert got == want, ('RA6 does not reproduce frozen main table', got, want)
        out['train_plus_tail_s'] = out['train_to_ready_s'] + out['queries']['negative_tail']['seconds']
        out['status'] = 'ok'
    except Exception:
        out['status'] = 'error'
        out['error'] = traceback.format_exc()
        print(out['error'], flush=True)
    S.finish(out, a.output)
    if out['status'] != 'ok':
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('dataset', choices=tuple(S.SETTINGS))
    p.add_argument('budget', type=int)
    p.add_argument('output', type=Path)
    p.add_argument('--scoring', choices=('loop', 'leaf'), required=True)
    p.add_argument('--chunk-rows', type=int, default=32768)
    a = p.parse_args()
    if a.output.exists(): p.error('Output exists; refusing overwrite')
    if a.chunk_rows < 1: p.error('chunk rows must be positive')
    main(a)

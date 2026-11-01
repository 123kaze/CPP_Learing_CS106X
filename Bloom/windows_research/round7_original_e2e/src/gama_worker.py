"""Execute the original Gama search verbatim; replace only its evaluation/output tail."""
import shared as S
import csv
import os
import sys
import time
import traceback
import numpy as np
import lightgbm as lgb
from threadpoolctl import threadpool_info

SOURCE = S.BLOOM / 'original_baselines' / 'gama' / 'run_gama_plbf_ada.py'
REPO = S.BLOOM / 'original_baselines' / 'repos' / 'Spatio-Temporal-Lab__LBF-Gama'


def main(a):
    out = dict(method='Gama(original)', dataset=a.dataset, budget_kib=a.budget, status='running',
               source_sha256=S.digest(SOURCE), lightgbm=lgb.__version__, jit_setup_s=0.)
    folder, meta = S.fixture(a.dataset)
    out['fixture'] = meta
    os.environ['GAMA_REPO'] = str(REPO)
    raw_out = a.output.parent / (a.output.stem + '_original')
    raw_out.mkdir(parents=True, exist_ok=True)
    read_start = time.perf_counter()

    def finish_gama(g):
        out['read_prepare_s'] = (g['start_time'] / 1e9) - read_start
        out['train_select_s'] = (time.perf_counter_ns() - g['start_time']) / 1e9
        booster, plbf = g['best_bst'], g['best_plbf']
        t = time.perf_counter()
        pos_scores = booster.predict(g['positive_items'], num_threads=1).tolist()
        plbf.insert_keys(g['positive_urls_list'], pos_scores)
        out['build_s'] = time.perf_counter() - t
        out['train_to_ready_s'] = (time.perf_counter_ns() - g['start_time']) / 1e9
        bf = [b for b in plbf.backup_bloom_filters if b is not None]
        out.update(trees=int(g['best_epoch']), model_pickle_bytes=int(g['model_size']),
                   bf_target_bits=float(g['size'] - g['model_size']) * 8,
                   bf_logical_bits=sum(b.num_bits_m for b in bf),
                   bf_array_payload_bytes=sum(len(b.backend.array_) * b.backend.array_.itemsize for b in bf),
                   bf_array_with_headers_bytes=sum(sys.getsizeof(b.backend.array_) for b in bf),
                   member_index_bytes=0, evaluated_epochs=sorted(int(e) for e in g['fpr_map']),
                   threadpools=threadpool_info())
        assert all(p['num_threads'] == 1 for p in out['threadpools']), out['threadpools']
        print(f'READY Gama(original) {a.dataset}: {out["train_to_ready_s"]:.2f}s trees={out["trees"]}', flush=True)
        t = time.perf_counter()
        # Canonical member order matches RA6, not Gama's train-members/remaining-members concatenation.
        member_ids = np.load(folder / 'member_ids.npy')
        query_ids = np.load(folder / 'query_ids.npy')
        pos_ids = np.asarray(g['positive_urls_list'], np.uint64)
        order = np.argsort(pos_ids)
        pos_map = order[np.searchsorted(pos_ids[order], member_ids)]
        assert np.array_equal(pos_ids[pos_map], member_ids)
        assert np.array_equal(np.asarray(g['query_urls'], np.uint64), query_ids)
        X = np.ascontiguousarray(np.vstack([g['positive_items'][pos_map], g['X_query']]))
        keys = np.concatenate([member_ids, query_ids]).tolist()
        nm = len(member_ids)
        out['query_input_prepare_s'] = time.perf_counter() - t

        def run(stream, lo, hi, state):
            idx = stream[lo:hi]
            scores = booster.predict(X[idx], num_threads=1)
            cnt = np.zeros(6, np.int64)
            for x, score in zip(idx, scores):
                ok = plbf.contains(keys[x], score)
                cnt[0] += ok
                cnt[1] += ok and x >= nm
                cnt[2] += not ok and x < nm
            cnt[4] = len(idx)
            return cnt

        t = time.perf_counter()
        fn = sum(not plbf.contains(k, sc) for k, sc in zip(g['positive_urls_list'], pos_scores))
        assert fn == 0, ('member false negatives', fn)
        out['member_false_negatives'] = fn
        out['verification_s'] = time.perf_counter() - t
        out['queries'] = S.evaluate(run, lambda: None, a.dataset)
        ref_file = S.ROOT.parent / 'round5_dp' / 'results' / f'rows_{a.dataset}_{a.budget}.csv'
        if ref_file.exists():
            ref = next((r for r in csv.DictReader(ref_file.open()) if r['method'] == 'Gama(original)'
                        and r['workload'] == meta['workload'] and r['seed'] == '0'), None)
            if ref:
                actual = out['queries']['negative_tail']['fp']
                out['previous_run_check'] = dict(actual=actual, expected=int(ref['fp_tail']),
                                                 equal=actual == int(ref['fp_tail']))
        out['train_plus_tail_s'] = out['train_to_ready_s'] + out['queries']['negative_tail']['seconds']
        out['status'] = 'ok'

    source = SOURCE.read_text()
    start = '    pos_scores = best_bst.predict(positive_items).tolist()'
    end = '  except Exception as e:'
    assert source.count(start) == 1 and source.count(end) == 1
    source = source[:source.index(start)] + '    finish_gama(globals())\n' + source[source.index(end):]
    sys.argv = [str(SOURCE), str(S.BLOOM / 'original_baselines' / 'gama' / 'data' / a.dataset),
                str(a.budget), str(raw_out)]
    try:
        exec(compile(source, str(SOURCE), 'exec'), {'__name__': '__main__', '__file__': str(SOURCE),
                                                  'finish_gama': finish_gama})
        if out['status'] != 'ok':
            error_file = raw_out / f'gama_{a.budget}.json'
            out['status'] = 'error'
            out['original_error'] = error_file.read_text() if error_file.exists() else 'No result from original driver'
    except Exception:
        out['status'] = 'error'
        out['error'] = traceback.format_exc()
        print(out['error'], flush=True)
    S.finish(out, a.output)
    if out['status'] != 'ok':
        raise SystemExit(1)


if __name__ == '__main__':
    main(S.arguments())

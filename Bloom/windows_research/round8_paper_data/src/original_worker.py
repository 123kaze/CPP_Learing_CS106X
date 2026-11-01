"""Authors' G-LBF or G-PLBF search, instrumented without rewriting its optimizer."""
import paper_common as P
import argparse
import os
import sys
import time
import traceback
import numpy as np
import pandas as pd
import lightgbm as lgb
from threadpoolctl import threadpool_info

REPO = P.BLOOM / 'original_baselines/repos/Spatio-Temporal-Lab__LBF-Gama'
os.environ['GAMA_REPO'] = str(REPO)
sys.path.insert(0, str(REPO))


def main(a):
    source_file = REPO / f'lgb_url_Gama{a.variant}_ada.py'
    out = dict(method=f'G-{a.variant}(original)', dataset=a.dataset, budget_kib=a.budget,
               source_sha256=P.S.digest(source_file), lightgbm=lgb.__version__, status='running')
    begin_read = time.perf_counter()
    def finish(g):
        t0 = g['start_time'] / 1e9
        out['read_prepare_s'] = t0 - begin_read
        booster = g['best_bst']
        if a.variant == 'PLBF':
            t = time.perf_counter()
            pos_scores = booster.predict(g['positive_items'], num_threads=1).tolist()
            bf = g['best_plbf']
            bf.insert_keys(g['positive_urls_list'], pos_scores)
            out['final_bf_build_s'] = time.perf_counter() - t
            accepts = bf.contains
            arrays = [b for b in bf.backup_bloom_filters if b is not None]
            out.update(bf_logical_bits=sum(b.num_bits_m for b in arrays),
                       bf_array_payload_bytes=sum(len(b.backend.array_) * b.backend.array_.itemsize for b in arrays))
        else:
            bf = g['bloom_filter']
            threshold = g['best_threshold']
            accepts = lambda key, score: score > threshold or key in bf
            out.update(threshold=float(threshold), bf_logical_bits=bf.num_bits,
                       bf_array_payload_bytes=len(bf.bitarray.tobytes()))
        out['train_to_ready_s'] = time.perf_counter() - t0
        out.update(trees=int(g['best_epoch']), model_pickle_bytes=int(g['model_size']),
                   bf_target_bits=float((a.budget * 1024 - g['model_size']) * 8),
                   theoretical_fpr=float(g['best_fpr']), threadpools=threadpool_info(), member_index_bytes=0)
        assert all(x['num_threads'] == 1 for x in out['threadpools'])
        t = time.perf_counter()
        Xm = np.concatenate([g['X_train'][g['y_train'] == 1], g['X_test'][g['y_test'] == 1]])
        km = pd.concat([g['train_urls'][g['y_train'] == 1], g['test_urls'][g['y_test'] == 1]])
        hm = pd.util.hash_pandas_object(km.astype(str), index=False).to_numpy(np.uint64)
        canonical = np.load(P.ROOT / 'inputs' / a.dataset / 'member_ids.npy')
        order = np.argsort(hm)
        indices = order[np.searchsorted(hm[order], canonical)]
        assert np.array_equal(hm[indices], canonical)
        hq = pd.util.hash_pandas_object(g['query_urls'].astype(str), index=False).to_numpy(np.uint64)
        assert np.array_equal(hq, np.load(P.ROOT / 'inputs' / a.dataset / 'query_ids.npy'))
        X = np.ascontiguousarray(np.vstack([Xm[indices], g['X_query']]))
        keys = np.concatenate([km.to_numpy()[indices], g['query_urls'].to_numpy()]).tolist()
        nm = len(canonical)
        out['query_input_prepare_s'] = time.perf_counter() - t
        def run(stream, lo, hi, state):
            idx = stream[lo:hi]
            scores = booster.predict(X[idx], num_threads=1)
            cnt = np.zeros(6, np.int64)
            for i, score in zip(idx, scores):
                accepted = accepts(keys[i], score)
                cnt[0] += accepted
                cnt[1] += accepted and i >= nm
                cnt[2] += not accepted and i < nm
            cnt[4] = len(idx)
            return cnt
        fn = 0
        for lo in range(0, nm, 1000):
            idx = np.arange(lo, min(nm, lo + 1000), dtype=np.int64)
            fn += int(run(idx, 0, len(idx), None)[2])
        assert fn == 0, ('member false negatives', fn)
        out['member_false_negatives'] = fn
        out['pool'] = P.full_pool(run, lambda: None, a.dataset)
        out['workloads'] = {}
        for name in ('once', 'zipf'):
            out['workloads'][name] = P.measure_queries(run, lambda: None, a.dataset, name)
        out['status'] = 'ok'
        print(f'COMPLETE {out["method"]} {a.dataset} {a.budget}: pool={out["pool"]["fpr"]:.6%}', flush=True)
    text = source_file.read_text()
    for file in ('url_train.csv', 'url_test.csv', 'url_query.csv'):
        text = text.replace(f"'dataset/{file}'", repr(str(P.ROOT / 'data' / a.dataset / file)))
    text = text.replace("'dataset/url_sample' + str(positive_frac) + '.csv'", repr(str(P.ROOT / 'data' / a.dataset / 'url_sample0.1.csv')))
    old = 'for size in range(64 * 1024, 320 * 1024 + 1, 64 * 1024):'
    assert text.count(old) == 1
    text = text.replace(old, f'for size in [{a.budget} * 1024]:')
    marker = '    pos_scores = best_bst.predict(positive_items).tolist()' if a.variant == 'PLBF' else '    end_time = time.perf_counter_ns()'
    assert text.count(marker) == 1
    text = text[:text.index(marker)] + '    finish(globals())\n'
    try:
        exec(compile(text, str(source_file), 'exec'), {'__name__':'__main__', '__file__':str(source_file), 'finish':finish})
    except Exception:
        out['status'] = 'error'
        out['error'] = traceback.format_exc()
        print(out['error'], flush=True)
    P.S.finish(out, a.output)
    if out['status'] != 'ok':
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('dataset')
    p.add_argument('budget', type=int)
    p.add_argument('variant', choices=('LBF', 'PLBF'))
    p.add_argument('output', type=P.Path)
    main(p.parse_args())

"""Run fixed no-model controls without modifying frozen methods. One cache per process."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import time
import numpy as np
import baseline as B

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = {'cod': (256, 1024, 4096), 'url': (64, 128, 256), 'shalla': (256, 1024, 2048, 4096)}
COLS = ['dataset', 'budget_kib', 'workload', 'seed', 'method', 'cache_mode', 'trees', 'frac',
        'cache_alloc_bytes', 'cache_slots', 'model_bytes', 'bf_bytes', 'metadata_bytes', 'overhead_bytes',
        'total_bytes', 'bits_per_member', 'k', 'fp_tail', 'tail_len', 'fpr_tail', 'static_fpr_pool',
        'learn_fp', 'learning_queries', 'distinct_learning_keys', 'select_s', 'candidates_build_check_s',
        'base_stream_sha256', 'tail_stream_sha256', 'case_s']


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def digest_array(a):
    return hashlib.sha256(np.ascontiguousarray(a).view(np.uint8)).hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def all_budgets(ds):
    if ds in SYNTHETIC:
        return SYNTHETIC[ds]
    meta = json.loads((B.WR / 'round11_tcp/results/datasets.json').read_text())
    return tuple(meta[ds]['budgets_kib'])


def run(a):
    begin = time.perf_counter()
    cache = B.CACHES[a.cache]
    B.E5.K = cache
    setup, safe, paths = B.load_setup(a.dataset, a.cache)
    budgets = tuple(map(int, a.budgets.split(','))) if a.budgets else all_budgets(a.dataset)
    specs = [('真实轨迹', None)] if a.dataset.endswith('_flow') else B.E5.workload_specs(len(setup.h1q))
    seeds = range(1 if a.dataset.endswith('_flow') else a.seeds)
    expected = {(kib, name, seed) for kib in budgets for name, _ in specs for seed in seeds}
    folder = ROOT / 'results' / a.tag / a.cache
    folder.mkdir(parents=True, exist_ok=True)
    params = dict(dataset=a.dataset, cache=a.cache, budgets=list(budgets), seeds=list(seeds), queries=a.queries,
                  cache_fracs=list(B.E5.FRACS), expected_cases=len(expected), numpy=np.__version__,
                  inputs={str(p.relative_to(B.WR.parent)): digest_file(p) for p in paths},
                  member_hashes_sha256=digest_array(setup.h1m), query_hashes_sha256=digest_array(setup.h1q),
                  query_score_sha256=digest_array(setup.q_score),
                  sources={str(p.relative_to(B.WR.parent)): digest_file(p) for p in
                           (Path(__file__), Path(B.__file__), Path(B.E5.__file__), Path(cache.__file__),
                            Path(B.C.__file__), Path(B.R.__file__),
                            B.WR / 'round2_backlog/src/engine.py',
                            B.WR.parent / 'learned_adaptive_hybrid/src/exp2_repetition_cache.py')},
                  protocol_sha256=digest_file(ROOT / 'plan/design-freeze.md'),
                  deployment_note='BF owning array + cache owning array; inputs/JIT/selection state excluded')
    meta_path = folder / f'{a.dataset}_inputs.json'
    if meta_path.exists() and json.loads(meta_path.read_text()) != params:
        raise RuntimeError('Inputs or runner changed; do not mix runs. Choose a new --tag.')
    save_json(meta_path, params)
    suffix = '-fp64' if a.cache == 'fp64' else ''
    methods = ('BF' + suffix, 'BF+ReplayCache' + suffix)
    completed = set()
    for kib in budgets:
        dest = folder / f'rows_{a.dataset}_{kib}.csv'
        records = []
        if dest.exists():
            with dest.open(encoding='utf-8') as fh:
                records = list(csv.DictReader(fh))
            unique = {(r['workload'], int(r['seed']), r['method']) for r in records}
            if len(unique) != len(records):
                raise RuntimeError(f'Duplicate rows: {dest}')
            for name, _ in specs:
                for seed in seeds:
                    present = {m for m in methods if (name, seed, m) in unique}
                    if present and present != set(methods):
                        raise RuntimeError(f'Partial case in {dest}: {name}/{seed}')
                    if present:
                        completed.add((kib, name, seed))
        if all((kib, name, seed) in completed for name, _ in specs for seed in seeds):
            continue
        build_start = time.perf_counter()
        candidates = [B.build(setup, kib, f, cache) for f in B.E5.FRACS]
        build_s = time.perf_counter() - build_start
        plain = candidates[0]
        assert plain['frac'] == 0
        for name, spec in specs:
            for seed in seeds:
                if (kib, name, seed) in completed:
                    continue
                start = time.perf_counter()
                base = B.E5.base_stream(setup, name, spec, seed, a.queries)
                n = len(base) // 4
                assert 0 < n < len(base)
                learn, base_tail = base[:n], base[n:]
                base_hash = digest_array(base)
                t = time.perf_counter()
                best, replay = B.E5.replay_best(candidates, learn, setup, safe)
                select_s = time.perf_counter() - t
                selected_learn_fp, cut = replay[best['trees'], best['frac']]
                assert not cut
                distinct = len(np.unique(learn))
                rows = []
                for method, c in zip(methods, (plain, best)):
                    st = c['structure']
                    tail = B.E5.tail_for(c, name, base_tail, seed)
                    measured = B.E5.evaluate(c, tail, setup, safe)
                    assert st.used_bytes <= kib * 1024
                    learn_fp = int(st.fp_static[learn].sum()) if c is plain else int(selected_learn_fp)
                    rows.append(dict(dataset=a.dataset, budget_kib=kib, workload=name, seed=seed,
                        method=method, cache_mode=a.cache, trees=0, frac=c['frac'],
                        cache_alloc_bytes=c['cache_bytes'], cache_slots=c['slots'], model_bytes=0,
                        bf_bytes=st.filter_bytes, metadata_bytes=st.metadata_bytes,
                        overhead_bytes=st.array_overhead_bytes, total_bytes=st.used_bytes,
                        bits_per_member=int(st.data[1]) / len(setup.h1m), k=int(st.data[2]),
                        fp_tail=measured['fp'], tail_len=len(tail), fpr_tail=measured['fp'] / len(tail),
                        static_fpr_pool=float(st.fp_static.mean()), learn_fp=learn_fp,
                        learning_queries=n, distinct_learning_keys=distinct,
                        select_s=select_s if method == methods[1] else 0,
                        candidates_build_check_s=build_s, base_stream_sha256=base_hash,
                        tail_stream_sha256=digest_array(tail), case_s=time.perf_counter() - start))
                records.extend(rows)
                temp = dest.with_suffix('.csv.tmp')
                with temp.open('w', encoding='utf-8', newline='') as fh:
                    writer = csv.DictWriter(fh, fieldnames=COLS)
                    writer.writeheader()
                    writer.writerows(records)
                    fh.flush()
                    os.fsync(fh.fileno())
                temp.replace(dest)
                completed.add((kib, name, seed))
                print(f"{a.dataset} {a.cache} {kib} {name} s{seed} BF={rows[0]['fp_tail']} "
                      f"BF+cache={rows[1]['fp_tail']} frac={best['frac']} cases={len(completed)}/{len(expected)}", flush=True)
    assert completed == expected, (len(completed), len(expected))
    save_json(folder / f'{a.dataset}_completion.json', dict(status='complete', cases=len(completed),
              rows=2 * len(completed), this_invocation_seconds=time.perf_counter() - begin,
              inputs_sha256=digest_file(meta_path)))
    print(f'COMPLETE {a.dataset} {a.cache}: {len(completed)} cases', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True, choices=tuple(SYNTHETIC) +
                   ('caida_tcp_flow', 'mawi2020_tcp_flow', 'mawi2021_tcp_flow', 'mawi2022_tcp_flow'))
    p.add_argument('--cache', choices=('index', 'fp64'), required=True)
    p.add_argument('--budgets')
    p.add_argument('--seeds', type=int, default=5)
    p.add_argument('--queries', type=int, default=10000000)
    p.add_argument('--tag', default='main')
    args = p.parse_args()
    if args.seeds < 1 or args.queries < 4:
        p.error('seeds >= 1 and queries >= 4 required')
    run(args)

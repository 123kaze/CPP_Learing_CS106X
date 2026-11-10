"""Reconstruct all eight timing rows from 72 verified records; stdlib only."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from statistics import median
from check14 import check_pair, check_archive, healthy

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = {'caida_flow': 24, 'url': 128, 'mawi2020_flow': 24, 'mawi2021_flow': 24,
            'mawi2022_flow': 24, 'caida': 256, 'shalla': 1024, 'cod': 1024}
METHODS = ('gama', 'loop', 'leaf')


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def optional_upstream(rel):
    return rel.startswith('original_baselines/repos/') or rel == 'original_baselines/gama/run_gama_plbf_ada.py'


def collect(root=ROOT, with_inputs=False):
    assert __debug__, 'Run without -O; assertions are required'
    bloom = root.parents[1]
    dest = root / 'results/main'
    files = {}
    missing_sources = []

    def load(p):
        files[str(p.relative_to(bloom))] = digest(p)
        return json.loads(p.read_text())

    manifest = load(root / 'results/manifest.json')
    freeze = load(root / 'plan/freeze.json')
    done = load(dest / 'completion.json')
    assert done == dict(status='complete', fresh_builds=72, exact_ra6_pairs=24, settings=8, reps=3,
                        manifest_sha256=digest(root / 'results/manifest.json'))
    assert manifest['settings'] == SETTINGS and manifest['reps'] == 3 and manifest['chunk_rows'] == 32768
    assert manifest['sources'] == freeze['sha256']
    for rel, want in manifest['sources'].items():
        p = bloom / rel
        if not p.is_file() and optional_upstream(rel) and not with_inputs:
            missing_sources.append(rel)
            continue
        assert digest(p) == want, rel
        files[rel] = want
    expected_inputs = set()
    for ds, kib in SETTINGS.items():
        expected_inputs.add(f'windows_research/round2_backlog/cache/{ds}/data.npz')
        expected_inputs.update(f'windows_research/round7_original_e2e/inputs/{ds}/{name}' for name in
                              ('meta.json', 'learn.npy', 'tail.npy', 'mixed.npy', 'member_ids.npy', 'query_ids.npy'))
        expected_inputs.update(f'original_baselines/gama/data/{ds}/{name}' for name in
                              ('url_train.csv', 'url_test.csv', 'url_query.csv', 'url_sample0.1.csv'))
        expected_inputs.add(f'windows_research/round6_bucket/results/main/rows_{ds}_{kib}.csv')
        expected_inputs.update(f'windows_research/round7_original_e2e/results/main/{ds}_{kib}_rep{rep}_{method}.json'
                               for rep in range(3) for method in ('gama', 'ra6'))
    assert set(manifest['inputs']) == expected_inputs
    if with_inputs:
        for rel, want in manifest['inputs'].items():
            assert digest(bloom / rel) == want, rel
            files[rel] = want
    names = {f'{ds}_{kib}_rep{rep}_{method}' for ds, kib in SETTINGS.items() for rep in range(3) for method in METHODS}
    for ext in ('.json', '.log'):
        assert {p.stem for p in dest.glob(f'*_rep*_*{ext}')} == names
    checks = []
    rows = []
    tables = []
    for ds, kib in SETTINGS.items():
        triples = []
        main_ref_path = bloom / f'windows_research/round6_bucket/results/main/rows_{ds}_{kib}.csv'
        assert digest(main_ref_path) == manifest['inputs'][str(main_ref_path.relative_to(bloom))]
        files[str(main_ref_path.relative_to(bloom))] = digest(main_ref_path)
        with main_ref_path.open(newline="") as f:
            main_refs = list(csv.DictReader(f))
        for rep in range(3):
            triple = {}
            for method in METHODS:
                p = dest / f'{ds}_{kib}_rep{rep}_{method}.json'
                r = load(p)
                healthy(r)
                assert (r['dataset'], r['budget_kib'], r['rep']) == (ds, kib, rep)
                env = manifest['environments']['gama' if method == 'gama' else 'loop']
                for key in ('python', 'numpy', 'lightgbm'): assert r[key] == env[key]
                assert r['platform'] == manifest['platform']
                if method != 'gama':
                    assert r['scoring'] == method and r['chunk_rows'] == 32768
                    assert r['worker_sha256'] == manifest['sources'][str((root / 'src/ra6_worker14.py').relative_to(bloom))]
                    assert r['leaf_helper_sha256'] == manifest['sources']['windows_research/round13_complete/src/leaf_scores.py']
                    ref = next(x for x in main_refs if x['method'] == 'RA6' and x['workload'] == r['fixture']['workload'] and x['seed'] == '0')
                    assert (r['trees'], r['cache_bytes'], r['queries']['negative_tail']['fp']) == (int(ref['trees']), int(ref['cache_alloc_bytes']), int(ref['fp_tail']))
                source = ('original_baselines/gama/run_gama_plbf_ada.py' if method == 'gama'
                          else 'windows_research/round6_bucket/src/ra6.py')
                assert r['source_sha256'] == manifest['sources'][source]
                log = p.with_suffix('.log')
                text = log.read_text()
                assert 'Traceback' not in text and f'COMPLETE {r["method"]} {ds} {kib}: ok' in text
                files[str(log.relative_to(bloom))] = digest(log)
                oldmethod = 'gama' if method == 'gama' else 'ra6'
                oldpath = bloom / f'windows_research/round7_original_e2e/results/main/{ds}_{kib}_rep{rep}_{oldmethod}.json'
                archived = load(oldpath)
                assert digest(oldpath) == manifest['inputs'][str(oldpath.relative_to(bloom))]
                check_archive(r, archived, method)
                triple[method] = r
                row = dict(dataset=ds, budget_kib=kib, rep=rep, method=method)
                for key in ('train_to_ready_s', 'train_plus_tail_s', 'process_wall_s', 'peak_rss_bytes', 'trees',
                            'member_index_bytes', 'train_s', 'score_prepare_s', 'select_build_s', 'executable_prepare_s',
                            'train_select_s', 'build_s', 'used_bytes', 'cache_bytes', 'model_pickle_bytes', 'bf_array_payload_bytes'):
                    row[key] = r.get(key, '')
                for name, q in r['queries'].items():
                    for key in ('seconds', 'queries', 'negatives', 'fp', 'fn', 'batch', 'ns_per_query'):
                        row[f'{name}_{key}'] = q[key]
                rows.append(row)
            result = check_pair(triple['loop'], triple['leaf'])
            assert triple['gama']['fixture'] == triple['leaf']['fixture']
            result['matches_round7_all_methods'] = True
            checks.append(result)
            triples.append(triple)
        def ratio(a, b, key, query=None):
            def get(r): return r['queries'][query][key] if query else r[key]
            values = [get(t[a]) / get(t[b]) for t in triples]
            return dict(median=median(values), min=min(values), max=max(values), values=values)
        stats = {}
        for method in METHODS:
            rr = [t[method] for t in triples]
            stats[method] = {key: median(r[key] for r in rr) for key in
                             ('train_to_ready_s', 'train_plus_tail_s', 'peak_rss_bytes')}
            stats[method]['queries'] = {name: {key: median(r['queries'][name][key] for r in rr)
                                                for key in ('seconds', 'fp', 'fn', 'queries', 'negatives')}
                                       for name in ('negative_tail', 'mixed_batch', 'mixed_scalar')}
        tables.append(dict(dataset=ds, budget_kib=kib, medians=stats,
                           loop_over_leaf_ready=ratio('loop', 'leaf', 'train_to_ready_s'),
                           leaf_over_gama_ready=ratio('leaf', 'gama', 'train_to_ready_s'),
                           gama_over_leaf_tail=ratio('gama', 'leaf', 'seconds', 'negative_tail'),
                           leaf_over_gama_ready_plus_tail=ratio('leaf', 'gama', 'train_plus_tail_s'),
                           leaf_over_loop_rss=ratio('leaf', 'loop', 'peak_rss_bytes')))
    assert len(rows) == 72 and len(checks) == 24
    assert checks == load(dest / 'pair_checks.json')
    return rows, tables, dict(status='verified', fresh_builds=72, exact_ra6_pairs=24,
                              checked_raw_inputs=with_inputs, unavailable_upstream_sources=missing_sources, sources=files)


def render(rows, tables):
    lines = ['# Round 14: optimized end-to-end timings on the eight main-table settings', '',
             '72 fresh processes: 8 settings × 3 repetitions × original G-PLBF / RA6-loop / RA6-leaf. '
             'All 24 RA6 pairs have identical model and 14-prefix score digests, selected configurations, '
             'filter payloads and native query counts. All methods match their corresponding round-7 archived configurations/counts. '
             'The separate 3-process pilot is excluded.', '',
             'Times are medians of 3 runs in seconds. Ratios are medians of the 3 paired ratios, not ratios of median times.', '',
             '## Construction', '',
             '| Dataset | KiB | Original ready s | Loop ready s | Leaf ready s | Loop/leaf speedup | Leaf/original cost ratio |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for s in tables:
        g, l, f = (s['medians'][m] for m in METHODS)
        lines.append(f"| {s['dataset']} | {s['budget_kib']} | {g['train_to_ready_s']:.3f} | {l['train_to_ready_s']:.3f} | {f['train_to_ready_s']:.3f} | {s['loop_over_leaf_ready']['median']:.3f}× | {s['leaf_over_gama_ready']['median']:.3f} |")
    lines += ['', '## Full negative tail and construction plus tail', '',
              '| Dataset | Original FP | Leaf FP | Original tail s | Leaf tail s | Tail speedup | Original ready+tail s | Leaf ready+tail s | Leaf/original total ratio |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in tables:
        g, f = (s['medians'][m] for m in ('gama', 'leaf'))
        a, b = g['queries']['negative_tail'], f['queries']['negative_tail']
        lines.append(f"| {s['dataset']} | {a['fp']} | {b['fp']} | {a['seconds']:.3f} | {b['seconds']:.3f} | {s['gama_over_leaf_tail']['median']:.3f}× | {g['train_plus_tail_s']:.3f} | {f['train_plus_tail_s']:.3f} | {s['leaf_over_gama_ready_plus_tail']['median']:.3f} |")
    lines += ['', '## Mixed-query timings', '',
              '| Dataset | Mode | Original s | Loop s | Leaf s | Original FP | Leaf FP | All FN |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for s in tables:
        for name in ('mixed_batch', 'mixed_scalar'):
            g, l, f = (s['medians'][m]['queries'][name] for m in METHODS)
            lines.append(f"| {s['dataset']} | {name} | {g['seconds']:.4f} | {l['seconds']:.4f} | {f['seconds']:.4f} | {g['fp']} | {f['fp']} | 0 |")
    lines += ['', '## Process peak RSS', '',
              '| Dataset | Original GiB | Loop GiB | Leaf GiB | Paired leaf/loop median |',
              '|---|---:|---:|---:|---:|']
    for s in tables:
        g, l, f = (s['medians'][m] for m in METHODS)
        lines.append(f"| {s['dataset']} | {g['peak_rss_bytes']/2**30:.3f} | {l['peak_rss_bytes']/2**30:.3f} | {f['peak_rss_bytes']/2**30:.3f} | {s['leaf_over_loop_rss']['median']:.3f} |")
    lines += ['', '## Interpretation and limitations', '',
              '- `ready` includes training, prefix scoring/input preparation, selection and executable-filter construction. Reading data, JIT warm-up, query-input assembly, hash/correctness checks and service queries are excluded and recorded separately. `process_wall_s` includes these and is not construction time.',
              '- Prefix scoring is the only algorithm-path change. Three repetitions are timing repetitions of the same data, not independent dataset samples; no new significance claim is made.',
              '- This round freshly measures the original implementation in the same serial campaign. Original G-PLBF still uses its own pickle/bitmap accounting and Python/LightGBM/bloom_filter path; RA6 uses compact arrays/Numba. Matching nominal budgets is not proof of matching physical bytes, and this is not a same-kernel algorithm ablation.',
              '- The verified-prefix cache still requires an out-of-budget 8-byte-per-member index. Whole-process RSS is not deployment memory. A bounded leaf-ID matrix does not imply lower RSS.',
              '- Paired RSS-ratio medians need not equal the ratio of the two RSS medians (notably COD). The query implementation is unchanged: changes in query timings across campaigns are remeasurements, not evidence that prefix-score preparation speeds up service queries.',
              '- The original UDP-member/TCP-negative trace construction is unchanged. These results do not replace the less favorable TCP-only comparison with ordinary BF+cache.',
              '- Full-tail evaluation starts from an empty cache. Mixed batch uses 200,000 queries at batch=1000; mixed scalar uses the first 20,000 at batch=1. These measurements must not be pooled.',
              '- Construction-plus-tail is measured computation only: it excludes database, network and backing-store lookup latency. Each total is computed within a run before taking its median.',
              '- The first round-14 launcher failed during input-path preflight before any training started. The failed version/logs remain in `../round14_main_e2e`; v2 corrects only the manifest cache path. No failed or slow measured repetition was discarded.',
              '- `timing_summary.json` retains every paired ratio and its range; `timing_rows.csv` retains every run. Data-free verification checks archived results and available sources; `--inputs` additionally requires all original sources and hashes all raw inputs. No upstream code is redistributed to make verification pass.']
    csvbuf = io.StringIO(newline='')
    writer = csv.DictWriter(csvbuf, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    return {'report.md': '\n'.join(lines) + '\n', 'timing_rows.csv': csvbuf.getvalue(),
            'timing_summary.json': json.dumps(tables, indent=2) + '\n'}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', action='store_true')
    p.add_argument('--verify-only', action='store_true')
    a = p.parse_args()
    rows, tables, verification = collect(with_inputs=a.inputs)
    for name, text in render(rows, tables).items():
        target = ROOT / 'results' / name
        if a.verify_only:
            assert target.read_bytes() == text.encode(), name
        else:
            target.write_bytes(text.encode())
    if not a.verify_only:
        (ROOT / 'results/verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print('PASS: 72 fresh builds, 24 exact pairs, all main-table/round7 regressions and 8 complete timing rows.')
    print('Raw inputs checked:', a.inputs, '; unavailable upstream source files:', len(verification['unavailable_upstream_sources']))

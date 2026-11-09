"""Verify the complete scoring archive with stdlib only; never start a worker.

Default: code, records, paired equivalence, round8 results and report arithmetic.
--inputs additionally hashes the large raw data/stream caches on the experiment host.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import median

from check_scoring import check

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = (1, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160, 200)
DATASETS = ('paper_url', 'paper_cod')
BUDGETS = (64, 128, 192, 256, 320)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def verify(root=ROOT, with_inputs=False):
    assert __debug__, 'Run without Python -O; assertions are required'
    wr = root.parent
    src = root / 'results/scoring'
    files = {}

    def tracked(path):
        files[str(path.relative_to(wr))] = digest(path)
        return path

    def load(path):
        return json.loads(tracked(path).read_text())

    freeze = load(root / 'plan/scoring-freeze.json')
    manifest = load(src / 'manifest.json')
    done = load(src / 'completion.json')
    assert done == dict(status='complete', fresh_builds=60, verified_pairs=30,
                        verified_workload_pairs=60, prefixes_per_pair=14,
                        manifest_sha256=digest(src / 'manifest.json'))
    assert manifest['datasets'] == list(DATASETS)
    assert manifest['budgets'] == list(BUDGETS)
    assert manifest['reps'] == 3 and manifest['chunk_rows'] == 32768
    expected_inputs = {f'round8_paper_data/data/{ds}/data.npz' for ds in DATASETS}
    expected_inputs.update(f'round8_paper_data/inputs/{ds}/{workload}_{part}.npy'
                           for ds in DATASETS for workload in ('once', 'zipf') for part in ('learn', 'tail'))
    assert set(manifest['inputs']) == expected_inputs
    assert manifest['sources'] == freeze['sha256']
    for rel, want in manifest['sources'].items():
        assert digest(tracked(wr / rel)) == want, rel
    if with_inputs:
        for rel, want in manifest['inputs'].items():
            assert digest(tracked(wr / rel)) == want, rel
    names = {f'{ds}_{kib}_{mode}_rep{rep}' for ds in DATASETS for kib in BUDGETS
             for rep in range(3) for mode in ('loop', 'leaf')}
    for extension in ('.json', '.log'):
        assert {p.stem for p in src.glob(f'paper_*{extension}')} == names, extension
    rows = []
    summaries = []
    checks = []
    speeds = {ds: [] for ds in DATASETS}
    rss_ratios = {ds: [] for ds in DATASETS}
    for ds in DATASETS:
        for kib in BUDGETS:
            pairs = []
            historical = []
            for rep in range(3):
                pair = {}
                for mode in ('loop', 'leaf'):
                    stem = f'{ds}_{kib}_{mode}_rep{rep}'
                    r = load(src / (stem + '.json'))
                    assert (r['dataset'], r['budget_kib'], r['rep'], r['scoring']) == (ds, kib, rep, mode)
                    assert r['status'] == 'ok' and r['exit_code'] == 0 and r['threads'] == 1
                    assert r['method'] == 'RA6' and r['chunk_rows'] == 32768
                    assert r['lightgbm'] == manifest['lightgbm'] and r['numpy'] == manifest['numpy']
                    assert r['platform'] == manifest['platform']
                    assert r['python'] == manifest['python'].split()[0]
                    for key, rel in (('source_sha256', 'round6_bucket/src/ra6.py'),
                                     ('worker_sha256', 'round13_complete/src/scoring_worker.py'),
                                     ('leaf_helper_sha256', 'round13_complete/src/leaf_scores.py')):
                        assert r[key] == manifest['sources'][rel], (stem, key)
                    assert set(r['score_sha256']) == set(map(str, PREFIXES)), stem
                    for value in (r['model_sha256'], *r['score_sha256'].values()):
                        assert re.fullmatch('[0-9a-f]{64}', value), stem
                    assert type(r['peak_rss_bytes']) is int and r['peak_rss_bytes'] > 0
                    for key in ('jit_setup_s', 'read_prepare_s', 'train_s', 'score_and_input_prepare_s',
                                'common_train_prepare_s', 'verification_hash_s', 'process_wall_s'):
                        assert math.isfinite(r[key]) and r[key] > 0, (stem, key)
                    assert math.isclose(r['common_train_prepare_s'], r['train_s'] + r['score_and_input_prepare_s'],
                                        rel_tol=1e-4, abs_tol=1e-3), stem
                    assert set(r['workloads']) == {'once', 'zipf'}
                    for workload, q in r['workloads'].items():
                        assert q['fn'] == q['member_false_negatives'] == 0
                        for key in ('fp', 'fn', 'queries', 'negatives', 'used_bytes', 'cache_bytes'):
                            assert type(q[key]) is int and q[key] >= 0, (stem, workload, key)
                        assert q['fp'] <= q['negatives'] <= q['queries']
                        assert q['cache_bytes'] <= q['used_bytes'] <= kib * 1024
                        for key in ('train_to_ready_s', 'select_executable_s'):
                            assert math.isfinite(q[key]) and q[key] > 0
                        assert q['train_to_ready_s'] == r['common_train_prepare_s'] + q['select_executable_s']
                        assert q['train_to_ready_s'] < r['process_wall_s']
                        rows.append(dict(dataset=ds, budget_kib=kib, rep=rep, mode=mode, workload=workload,
                                         train_s=r['train_s'], score_and_input_prepare_s=r['score_and_input_prepare_s'],
                                         select_executable_s=q['select_executable_s'], train_to_ready_s=q['train_to_ready_s'],
                                         process_wall_s=r['process_wall_s'], peak_rss_bytes=r['peak_rss_bytes'],
                                         trees=q['trees'], cache_bytes=q['cache_bytes'], fp=q['fp']))
                    log = tracked(src / (stem + '.log')).read_text()
                    assert f'COMPLETE RA6 {ds} {kib}: ok' in log and 'Traceback' not in log, stem
                    pair[mode] = r
                result = check(pair['loop'], pair['leaf'])
                archived = load(wr / f'round8_paper_data/results/{ds}_{kib}_RA6_rep{rep}.json')
                assert archived['status'] == 'ok'
                for workload in ('once', 'zipf'):
                    a, b = archived['workloads'][workload], pair['loop']['workloads'][workload]
                    for key in ('trees', 'frac', 'cache_bytes', 'used_bytes', 'fp', 'fn', 'queries'):
                        assert a[key] == b[key], ('round8', ds, kib, rep, workload, key)
                    if workload == 'once':
                        assert a['pool']['fp'] == b['pool']['fp']
                    speeds[ds].append(b['train_to_ready_s'] / pair['leaf']['workloads'][workload]['train_to_ready_s'])
                rss_ratios[ds].append(pair['leaf']['peak_rss_bytes'] / pair['loop']['peak_rss_bytes'])
                result.update(matches_round8_configs_and_counts=True, rep=rep)
                checks.append(result)
                pairs.append(pair)
                historical.append(load(wr / f'round8_paper_data/results/{ds}_{kib}_PLBF_rep{rep}.json'))
            for workload in ('once', 'zipf'):
                a = [p['loop']['workloads'][workload]['train_to_ready_s'] for p in pairs]
                b = [p['leaf']['workloads'][workload]['train_to_ready_s'] for p in pairs]
                ratios = [x / y for x, y in zip(a, b)]
                summaries.append(dict(dataset=ds, budget_kib=kib, workload=workload,
                                      loop_median_ready_s=median(a), leaf_median_ready_s=median(b),
                                      median_paired_speedup=median(ratios), paired_speedup_range=[min(ratios), max(ratios)],
                                      loop_median_score_prepare_s=median(p['loop']['score_and_input_prepare_s'] for p in pairs),
                                      leaf_median_score_prepare_s=median(p['leaf']['score_and_input_prepare_s'] for p in pairs),
                                      historical_original_gplbf_median_s=median(h['train_to_ready_s'] for h in historical)))
    assert load(src / 'pair_checks.json') == checks
    assert load(root / 'results/scoring_summary.json') == summaries
    with tracked(root / 'results/scoring_rows.csv').open(newline='') as f:
        actual = list(csv.DictReader(f))
    assert len(actual) == len(rows) == 120
    for a, b in zip(actual, rows):
        assert a == {key: str(value) for key, value in b.items()}, (a, b)
    # Verify every displayed timing row as well as the machine-readable summaries.
    report = tracked(root / 'results/scoring_report.md').read_text()
    for s in summaries:
        line = (f"| {s['dataset']} | {s['budget_kib']} | {s['workload']} | {s['loop_median_ready_s']:.3f} | "
                f"{s['leaf_median_ready_s']:.3f} | {s['median_paired_speedup']:.2f}x | "
                f"{s['loop_median_score_prepare_s']:.3f} | {s['leaf_median_score_prepare_s']:.3f} |")
        assert report.count(line) == 1, line
    return dict(status='verified', fresh_builds=60, verified_pairs=len(checks), workload_records=len(rows),
                prefixes_per_pair=14, checked_raw_inputs=with_inputs,
                ready_speedup={ds: dict(min=min(x), median=median(x), max=max(x), faster=sum(v > 1 for v in x), count=len(x))
                               for ds, x in speeds.items()},
                paired_leaf_over_loop_rss_median={ds: median(x) for ds, x in rss_ratios.items()},
                sources=files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', action='store_true')
    parser.add_argument('--output', type=Path, help='Optional new verification record; refuses overwrite')
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('Output exists; refusing overwrite')
    result = verify(with_inputs=args.inputs)
    if args.output:
        with args.output.open('x') as f:
            json.dump(result, f, indent=2)
            f.write('\n')
    print('PASS: 60 builds, 30 exact pairs, round8 matches, 120 workload rows, hashes and timing arithmetic.')
    print(json.dumps({k: v for k, v in result.items() if k != 'sources'}, indent=2))

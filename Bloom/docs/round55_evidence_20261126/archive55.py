"""Standard-library, data-free release verification; does not replay experiments.

--create-manifest writes a new explicit publication manifest, never overwriting.
--verify checks that manifest, archived evidence, exported rows and available
frozen inputs. Missing data/model caches are listed as NOT CHECKED.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import math
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'archive_manifest.json'
ROUND = ROOT / 'windows_research/round55_exact_full_main_v4'
DIRECTORIES = (
    'windows_research/round54_review_suite',
    'windows_research/round55_exact_full_main',
    'windows_research/round55_exact_full_main_v2',
    'windows_research/round55_exact_full_main_v3',
    'windows_research/round55_exact_full_main_v4',
    'docs/round55_evidence_20261126',
)
DOCUMENTS = (
    'docs/round55_release_20261126.md',
    'docs/无索引主实验全量重跑_TODO_20261125.md',
    'docs/无索引主实验_图表映射_20261125.md',
    'docs/审查补充实验_TODO_20261125.md',
    'docs/审查补充实验_清理回执_20261125.json',
    'docs/SIS五月可重建原始文件_授权清理回执_20261125.json',
)
SUFFIXES = {'.py', '.md', '.json', '.csv', '.log', '.png', '.pdf'}


def auditor():
    spec = importlib.util.spec_from_file_location('release_audit55', HERE / 'audit55.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_path(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('non-relative archive path: ' + name)
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('archive path escapes root: ' + name)
    return path


def selected_files():
    files = set()
    for name in DIRECTORIES:
        folder = ROOT / name
        if not folder.is_dir():
            raise ValueError('missing release directory: ' + name)
        for p in folder.rglob('*'):
            if '__pycache__' in p.parts or p == MANIFEST or not p.is_file():
                continue
            if p.suffix not in SUFFIXES and p.name != '.gitignore':
                raise ValueError('unclassified publication file: ' + str(p))
            files.add(p)
    files.update(ROOT / name for name in DOCUMENTS)
    r56 = ROOT / 'windows_research/round56_exact_selection'
    files.update((r56 / 'src').glob('*.py'))
    files.update((r56 / 'plan').glob('*'))
    files.add(r56 / '.gitignore')
    # No round56 README/results/logs: this is the fixed code-only snapshot.
    for p in files:
        safe_path(ROOT, str(p.relative_to(ROOT)))
        if not p.is_file():
            raise ValueError('missing release file: ' + str(p))
    return sorted(files)


def verify_files(root, entries, a):
    a.check(len(entries) == len({e['path'] for e in entries}), 'duplicate manifest paths')
    total = 0
    for e in entries:
        p = safe_path(root, e['path'])
        a.check(p.is_file(), 'missing release file: ' + e['path'])
        a.check(p.stat().st_size == e['bytes'] and a.sha(p) == e['sha256'], 'release digest: ' + e['path'])
        total += e['bytes']
    return total


def verify(a):
    manifest = a.read(MANIFEST)
    entries = manifest['files']
    total = verify_files(ROOT, entries, a)
    a.check({e['path'] for e in entries} == {str(p.relative_to(ROOT)) for p in selected_files()}, 'explicit release scope')
    a.check(a.read(ROUND / 'results/completion.json')['status'] == 'complete', 'round55 completion')
    # Reuse the existing read-only auditor without modifying it. Its partial
    # mode avoids requiring unpublished data; full coverage is enforced below.
    with tempfile.TemporaryDirectory(prefix='round55-archive-') as tmp:
        out = Path(tmp)
        with contextlib.redirect_stdout(io.StringIO()):
            a.run(ROUND, out, partial=True)
        report = a.read(out / 'verification.json')
        verified = a.readcsv(out / 'verified_cases.csv')
    for field, value in (
        ('cases', 1150), ('completed_settings', 34), ('main_cases', 1146),
        ('probe_cases', 70), ('rows', 16100), ('ablations', 4188),
        ('top10_records', 11500), ('weighted_records', 41666),
        ('Gama_regressions', 1150), ('stacked_regressions', 1146),
        ('round53_case_regressions', 62),
    ):
        a.check(report[field] == value, 'complete archive coverage: ' + field)
    exports = {name: [] for name in ('rows.csv', 'ablations.csv', 'top10_predictions.csv', 'full_weighted_predictions.csv')}
    cases = a.read(ROUND / 'plan/cases.json')
    for setting in cases['settings']:
        folder = ROUND / f"results/{setting['dataset']}_{setting['budget_kib']}"
        for i, case in enumerate(setting['cases']):
            item = a.read(folder / f'case_{i:03d}.json')
            base = {k: case[k] for k in a.IDENTITY + ('cohort',)}
            stage1 = next(r['fp'] for r in item['rows'] if r['method'] == 'RA-stage1')
            exports['rows.csv'].extend(dict(cohort=case['cohort'], **r) for r in item['rows'])
            exports['ablations.csv'].extend(dict(**base, reference_stage1_fp=stage1, **r) for r in item['ablations'])
            exports['top10_predictions.csv'].extend(dict(**base, **r) for r in item['top10'])
            exports['full_weighted_predictions.csv'].extend(dict(**base, **r) for r in item['weighted_full'])
    for name, rows in exports.items():
        a.csv_equal(ROUND / 'results' / name, rows)
    totals = a.readcsv(ROUND / 'results/table_main_totals.csv')
    identities = {(r['dataset'], int(r['budget_kib']), r['method']) for r in totals}
    expected = {(s['dataset'], s['budget_kib'], m) for s in cases['settings'] for m in a.METHODS}
    a.check(len(totals) == 476 and identities == expected, 'main totals exact coverage')
    for r in totals:
        groups = defaultdict(list)
        for c in verified:
            if c['dataset'] == r['dataset'] and c['budget_kib'] == r['budget_kib'] and c['group'] != 'probe':
                groups[c['workload']].append(int(c[r['method']]))
        want = sum(statistics.fmean(v) for v in groups.values())
        a.check(math.isclose(want, float(r['FP_sum_of_seed_means']), rel_tol=1e-12, abs_tol=1e-9), 'seed-mean main totals')
    frozen = {}
    for name in ('round55_exact_full_main_v4', 'round56_exact_selection'):
        freeze = a.read(ROOT / 'windows_research' / name / 'plan/freeze.json')
        sources_checked = 0
        for path, digest in freeze['sources'].items():
            a.check(a.sha(safe_path(ROOT, path)) == digest, 'frozen source: ' + path)
            sources_checked += 1
        checked, missing = [], []
        for path, digest in freeze['inputs'].items():
            p = safe_path(ROOT, path)
            if not p.is_file():
                missing.append(path)
            else:
                a.check(a.sha(p) == digest, 'available frozen input: ' + path)
                checked.append(path)
        frozen[name] = dict(source_hashes_checked=sources_checked,
                            input_hashes_checked=len(checked),
                            inputs_NOT_CHECKED_missing=missing)
    return dict(status='data_free_release_archive_verified', files=len(entries), bytes=total,
                cases=1150, rows=16100, ablations=4188, top10_records=11500,
                weighted_records=41666, frozen=frozen,
                limitations=[
                    'Not a new execution of queries or timing measurements.',
                    'Missing raw/prepared/model inputs are NOT CHECKED; the host full-input receipt is separate.',
                    'Round56 code/protocol only; no round56 results are certified or published in this snapshot.',
                    'Replay est_fpr secondary tie-break is not independently reconstructible from saved records.',
                ])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--create-manifest', action='store_true')
    mode.add_argument('--verify', action='store_true')
    args = p.parse_args()
    a = auditor()
    if args.create_manifest:
        files = [dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size, sha256=a.sha(p)) for p in selected_files()]
        result = dict(schema=1, release_date='2026-11-26',
                      scope='round55 complete; round54 paused draft; round56 frozen code/protocol only',
                      exclusions=['raw datasets', 'prepared/model/JIT caches', 'round56 results/logs/README',
                                  'manuscript', 'unrelated files', 'this manifest itself'], files=files)
        a.writejson(MANIFEST, result)
        print(json.dumps(dict(status='manifest_created', files=len(files), bytes=sum(f['bytes'] for f in files))))
    else:
        print(json.dumps(verify(a), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

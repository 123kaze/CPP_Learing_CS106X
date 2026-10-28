"""Read-only original-results audit and integrity snapshots. Writes only windows_research."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
PROTECTED = ('research', 'learned_adaptive_hybrid')


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def snapshot():
    rows = []
    start = time.monotonic()
    for name in PROTECTED:
        for path in sorted((REPO / name).rglob('*')):
            if not path.is_file():
                continue
            s = path.stat()
            rows.append({'path': path.relative_to(REPO).as_posix(), 'size': s.st_size,
                         'mtime_ns': s.st_mtime_ns, 'sha256': digest(path)})
            if len(rows) % 500 == 0:
                print(f'hashed {len(rows)} files ({sum(r["size"] for r in rows):,} bytes)', flush=True)
    return {'created_local': time.strftime('%Y-%m-%d %H:%M:%S'), 'files': rows,
            'file_count': len(rows), 'bytes': sum(r['size'] for r in rows),
            'elapsed_s': time.monotonic() - start}


def archive_info(path):
    with zipfile.ZipFile(path) as z:
        files = z.infolist()
        row_matches = []
        for f in files:
            if f.filename.startswith('results/') and '/rows' in f.filename and f.filename.endswith('.json'):
                local = REPO / 'learned_adaptive_hybrid' / f.filename
                row_matches.append({'entry': f.filename, 'local_exists': local.exists(),
                                    'same_bytes': local.exists() and local.read_bytes() == z.read(f),
                                    'same_json': local.exists() and json.loads(local.read_text(encoding='utf-8')) == json.loads(z.read(f))})
        return {'path': str(path), 'sha256': digest(path), 'file_count': len(files),
                'compressed_bytes': path.stat().st_size,
                'uncompressed_bytes': sum(f.file_size for f in files),
                'entries': [{'name': f.filename, 'bytes': f.file_size} for f in files],
                'raw_data_or_weights_entries': [f.filename for f in files
                    if f.filename.lower().endswith(('.csv', '.npz', '.npy', '.pcap', '.gz'))
                    or Path(f.filename).name.lower() in ('model48.txt', 'model200.txt')],
                'row_file_comparison': row_matches}


def audit():
    src = REPO / 'learned_adaptive_hybrid'
    rows = []
    for p in sorted((src / 'results' / 'exp11_original_baselines').glob('rows_*.json')):
        for r in json.loads(p.read_text(encoding='utf-8')):
            if r['method'] == 'Stacked(原版)':
                rows.append(dict(r, source=p.relative_to(REPO).as_posix(),
                                 actual_bytes=r['frac'] * r['budget_kib'] * 1024,
                                 budget_status='over_budget' if r['frac'] > 1 else 'within_budget'))
    by_setting = []
    for ds, b in sorted({(r['dataset'], r['budget_kib']) for r in rows}):
        rr = [r for r in rows if r['dataset'] == ds and r['budget_kib'] == b]
        by_setting.append({'dataset': ds, 'budget_kib': b, 'runs': len(rr),
                           'over_budget_runs': sum(r['frac'] > 1 for r in rr),
                           'min_actual_budget_ratio': min(r['frac'] for r in rr),
                           'max_actual_budget_ratio': max(r['frac'] for r in rr)})
    bench = []
    for p in sorted((src / 'results' / 'bench_cache_overhead').glob('*.json')):
        r = json.loads(p.read_text(encoding='utf-8'))
        r['physical_table_bytes'] = r['table_slots'] * 16
        r['nominal_cache_bytes'] = r['budget_kib'] * 1024 * r['cache_frac']
        r['physical_nominal_ratio'] = r['physical_table_bytes'] / r['nominal_cache_bytes']
        bench.append(r)
    mawi = []
    for p in sorted((src / 'results').rglob('*mawi*.json')):
        try:
            content = json.loads(p.read_text(encoding='utf-8'))
            n = len(content)
        except Exception:
            n = None
        mawi.append({'file': p.relative_to(REPO).as_posix(), 'rows_or_keys': n})
    archives = []
    for p in [Path('E:/Download/Browser Download/results 2.zip'), src / 'results 2.zip']:
        if p.exists():
            archives.append(archive_info(p))
    result = {'stacked_rows': rows, 'stacked_summary': by_setting,
              'stacked_runs': len(rows), 'stacked_over_budget_runs': sum(r['frac'] > 1 for r in rows),
              'stacked_over_budget_threshold_counts': {str(t): sum(r['frac'] > t for r in rows)
                                                     for t in (1, 1.01, 1.05, 1.1, 2, 3, 5)},
              'cache_microbench': bench, 'mawi_existing_results': mawi,
              'mawi_holdout_verdict': 'Already inspected and reported; cannot certify an untouched holdout from available provenance.',
              'archives': archives,
              'physical_accounting_findings': [
                  'common.Structure.bits is np.uint8 per logical BF bit (8x bit-payload allocation in the simulator).',
                  'TREE_BYTES=700 is a model accounting convention; model, PLBF metadata, Python/Numba arrays and member index are excluded.',
                  'Setup.cache_cost stores safe-prefix length plus six bits, without empty slots, hash-table metadata or replacement metadata.',
                  'bench_cache_overhead uses uint64 hash and int64 length per slot, 16 bytes total.',
                  'Sorted-member-hash index needs at least 8 bytes/member; original code does not charge it to cache budget.',
                  'SKETCH_BYTES=5128 assumes byte HLL and 32-bit Space-Saving fields; current measurement uses int64: HLL pair 16384B + three 256-entry int64 arrays 6144B = 22528B (plus scalar counter).',
                  'No dynamic-member insertion/update API was found; safe-prefix computation verifies against a fixed complete member set.',
                  'Original MAWI report states no parameter tuning, but there is no timestamped pre-run code/parameter freeze hash.'
              ]}
    dump(ROOT / 'results/audit_existing.json', result)
    csv_lines = ['dataset,budget_kib,runs,over_budget_runs,min_actual_budget_ratio,max_actual_budget_ratio']
    for x in by_setting:
        csv_lines.append(','.join(str(x[k]) for k in ['dataset','budget_kib','runs','over_budget_runs','min_actual_budget_ratio','max_actual_budget_ratio']))
    (ROOT / 'results/stacked_budget_audit.csv').write_text('\n'.join(csv_lines) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['stacked_runs','stacked_over_budget_runs','stacked_summary','cache_microbench','mawi_holdout_verdict']}, ensure_ascii=False, indent=2))


def verify():
    before = json.loads((ROOT / 'evidence/protected-before.json').read_text(encoding='utf-8'))
    after = snapshot()
    b = {x['path']: x for x in before['files']}
    a = {x['path']: x for x in after['files']}
    added = sorted(a.keys() - b.keys())
    missing = sorted(b.keys() - a.keys())
    changed = sorted(p for p in a.keys() & b.keys() if a[p]['sha256'] != b[p]['sha256'])
    metadata_changed = sorted(p for p in a.keys() & b.keys() if a[p]['mtime_ns'] != b[p]['mtime_ns'])
    result = {'unchanged': not (added or missing or changed or metadata_changed),
              'protected_folders': list(PROTECTED), 'before_files': len(b), 'after_files': len(a),
              'added': added, 'missing': missing, 'changed': changed, 'metadata_changed': metadata_changed,
              'after': after}
    dump(ROOT / 'evidence/protected-verification.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'after'}, ensure_ascii=False, indent=2))
    if not result['unchanged']:
        raise SystemExit(1)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['audit','snapshot','verify'])
    args = ap.parse_args()
    if args.command == 'snapshot':
        out = snapshot()
        dump(ROOT / 'evidence/protected-before.json', out)
        print(json.dumps({k:v for k,v in out.items() if k != 'files'}, ensure_ascii=False, indent=2))
    elif args.command == 'verify':
        verify()
    else:
        audit()

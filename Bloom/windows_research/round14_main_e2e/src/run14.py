"""Run a correctness pilot, then 72 serial fresh builds on the eight main settings."""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from check14 import check_pair, check_archive, healthy

ROOT = Path(__file__).resolve().parents[1]
BLOOM = ROOT.parents[1]
OLD = ROOT.parent / 'round7_original_e2e'
SETTINGS = {'caida_flow': 24, 'url': 128, 'mawi2020_flow': 24, 'mawi2021_flow': 24,
            'mawi2022_flow': 24, 'caida': 256, 'shalla': 1024, 'cod': 1024}
ORDERS = (('loop', 'leaf', 'gama'), ('leaf', 'gama', 'loop'), ('gama', 'loop', 'leaf'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def interpreter(method):
    return BLOOM / ('.condaenv_gama' if method == 'gama' else '.condaenv') / 'bin/python'


def manifest():
    freeze = json.loads((ROOT / 'plan/freeze.json').read_text())
    for rel, want in freeze['sha256'].items(): assert digest(BLOOM / rel) == want, rel
    inputs = {}
    for ds, kib in SETTINGS.items():
        paths = [BLOOM / f'learned_adaptive_hybrid/cache/{ds}/data.npz']
        paths += [OLD / 'inputs' / ds / name for name in ('meta.json', 'learn.npy', 'tail.npy', 'mixed.npy', 'member_ids.npy', 'query_ids.npy')]
        paths += [BLOOM / 'original_baselines/gama/data' / ds / name for name in ('url_train.csv', 'url_test.csv', 'url_query.csv', 'url_sample0.1.csv')]
        paths += [ROOT.parent / f'round6_bucket/results/main/rows_{ds}_{kib}.csv']
        paths += [OLD / f'results/main/{ds}_{kib}_rep{rep}_{method}.json' for rep in range(3) for method in ('gama', 'ra6')]
        for path in paths: inputs[str(path.relative_to(BLOOM))] = digest(path)
        meta = json.loads((OLD / 'inputs' / ds / 'meta.json').read_text())
        for part in ('learn', 'tail', 'mixed'):
            assert inputs[str((OLD / 'inputs' / ds / f'{part}.npy').relative_to(BLOOM))] == meta[f'{part}_sha256']
        print(f'INPUTS VERIFIED {ds}', flush=True)
    probe = 'import json,platform,numpy,lightgbm; print(json.dumps(dict(python=platform.python_version(),numpy=numpy.__version__,lightgbm=lightgbm.__version__)))'
    envs = {m: json.loads(subprocess.check_output([str(interpreter(m)), '-c', probe], text=True)) for m in ('loop', 'gama')}
    return dict(settings=SETTINGS, reps=3, chunk_rows=32768, orders=ORDERS,
                sources=freeze['sha256'], inputs=inputs, environments=envs,
                platform=platform.platform(), hardware=subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True).strip(),
                note='Round7 fixtures and query protocol; fresh original Gama plus paired RA6 loop/leaf; pilot excluded.')


def worker(folder, ds, kib, rep, method):
    out = folder / f'{ds}_{kib}_rep{rep}_{method}.json'
    if out.exists():
        row = json.loads(out.read_text())
        assert row.get('rep') == rep and row.get('exit_code') == 0 and row.get('status') == 'ok' and 'process_wall_s' in row, f'Failed/incomplete existing result: {out}'
        healthy(row)
        print(f'SKIP COMPLETE {out.name}', flush=True)
        return row
    log = out.with_suffix('.log')
    assert not log.exists(), f'Existing unfinished log, no automatic retry: {log}'
    script = OLD / 'src/gama_worker.py' if method == 'gama' else ROOT / 'src/ra6_worker14.py'
    cmd = [str(interpreter(method)), '-u', str(script), ds, str(kib), str(out)]
    if method != 'gama': cmd += ['--scoring', method, '--chunk-rows', '32768']
    print(f'START {folder.name} {ds} {kib} rep{rep} {method}', flush=True)
    start = time.perf_counter()
    with log.open('x') as f: proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    elapsed = time.perf_counter() - start
    row = json.loads(out.read_text()) if out.exists() else dict(status='error', error=f'worker exit {proc.returncode}')
    row.update(rep=rep, process_wall_s=elapsed, exit_code=proc.returncode, loadavg_after=os.getloadavg())
    save(out, row)
    if proc.returncode or row.get('status') != 'ok':
        print(f'FAILED {out.name}: exit={proc.returncode}; see {log}', flush=True)
        raise SystemExit(1)
    healthy(row)
    print(f'COMPLETE {folder.name} {ds} {kib} rep{rep} {method}: process={elapsed:.1f}s', flush=True)
    return row


def triple(folder, ds, kib, rep):
    rows = {m: worker(folder, ds, kib, rep, m) for m in ORDERS[rep]}
    result = check_pair(rows['loop'], rows['leaf'])
    for method, row in rows.items():
        oldmethod = 'gama' if method == 'gama' else 'ra6'
        old = json.loads((OLD / f'results/main/{ds}_{kib}_rep{rep}_{oldmethod}.json').read_text())
        check_archive(row, old, method)
        assert row['fixture'] == rows['leaf']['fixture']
    result['matches_round7_all_methods'] = True
    print(f'CHECKED {folder.name} {ds} {kib} rep{rep}: 14 exact prefixes, payloads, native FPs, main table and round7', flush=True)
    return result


def main():
    assert __debug__, 'Do not disable verification assertions'
    assert json.loads((ROOT.parent / 'round13_complete/results/scoring/completion.json').read_text())['status'] == 'complete'
    mp = ROOT / 'results/manifest.json'
    cfg = json.loads(json.dumps(manifest()))
    if mp.exists(): assert json.loads(mp.read_text()) == cfg, 'Changed sources/inputs/environment; do not mix runs'
    else: save(mp, cfg)
    pd = ROOT / 'results/pilot'
    pd.mkdir(exist_ok=True)
    pilot = triple(pd, 'caida_flow', 24, 0)
    save(pd / 'completion.json', dict(status='complete', fresh_builds=3, checked=pilot))
    print('PILOT PASSED; starting 72 formal builds', flush=True)
    dest = ROOT / 'results/main'
    dest.mkdir(exist_ok=True)
    checks = []
    for ds, kib in SETTINGS.items():
        for rep in range(3):
            checks.append(triple(dest, ds, kib, rep))
            save(dest / 'pair_checks.json', checks)
    assert len(checks) == 24
    outputs = list(dest.glob('*_rep*_*.json'))
    assert len(outputs) == 72
    for path in outputs: healthy(json.loads(path.read_text()))
    save(dest / 'completion.json', dict(status='complete', fresh_builds=72, exact_ra6_pairs=24,
                                        settings=8, reps=3, manifest_sha256=digest(mp)))
    print('ROUND14 COMPLETE: 72 fresh builds, 24 exact RA6 pairs, 24 fresh original-Gama builds', flush=True)


if __name__ == '__main__':
    try: main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise SystemExit(1)

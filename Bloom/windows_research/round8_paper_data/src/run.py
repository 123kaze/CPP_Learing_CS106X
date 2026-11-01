"""Serialized paper-source re-evaluation, after the older timing experiment ends."""
import paper_common as P
import argparse
import datetime
import json
import subprocess
import time


def command(cmd, log):
    start = time.perf_counter()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as f:
        proc = subprocess.run([str(x) for x in cmd], stdout=f, stderr=subprocess.STDOUT)
    return proc.returncode, time.perf_counter() - start


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--after-round7', action='store_true')
    p.add_argument('--datasets', default='paper_url,paper_cod')
    p.add_argument('--budgets', default='64,128,192,256,320')
    p.add_argument('--reps', type=int, default=3)
    a = p.parse_args()
    dest = P.ROOT / 'results'
    dest.mkdir(parents=True, exist_ok=True)
    if a.after_round7:
        source = P.ROOT.parent / 'round7_original_e2e' / 'results' / 'main'
        deadline = time.monotonic() + 21600
        print('QUEUED: waiting for the 48 round7 worker results, no concurrent timing', flush=True)
        while True:
            rows = [json.loads(f.read_text()) for f in source.glob('*_rep*_*.json')]
            if any(r['status'] != 'ok' for r in rows):
                raise RuntimeError('Round7 worker failed: inspect before starting another timing run')
            if len(rows) == 48 and all('process_wall_s' in r for r in rows):
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Round7 did not complete within six hours')
            time.sleep(10)
    datasets = a.datasets.split(',')
    budgets = [int(x) for x in a.budgets.split(',')]
    py = P.BLOOM / '.condaenv' / 'bin' / 'python'
    pyg = P.BLOOM / '.condaenv_gama' / 'bin' / 'python'
    if a.after_round7:
        smoke_script = P.ROOT.parent / 'round7_original_e2e' / 'src' / 'run.py'
        ret, elapsed = command([py, '-u', smoke_script, '--datasets', 'caida_flow', '--budget', 16,
                                '--reps', 1, '--suffix', 'smoke16'], dest / 'round7_smoke16.log')
        print(f'16KiB diagnostic finished: exit={ret}, wall={elapsed:.1f}s; expected original failure is recorded', flush=True)
    sources = {f.name:P.S.digest(f) for f in (P.ROOT / 'src').glob('*.py')}
    config = dict(datasets=datasets, budgets=budgets, reps=a.reps)
    manifest = dest / 'manifest.json'
    if manifest.exists():
        old = json.loads(manifest.read_text())
        assert old['config'] == config and old['sources'] == sources, 'Do not mix changed experiment code/configurations'
    else:
        P.S.save(manifest, dict(config=config, sources=sources, started=datetime.datetime.now().isoformat()))
    for ds in datasets:
        audit = P.ROOT / 'data' / ds / 'audit.json'
        if not audit.exists():
            ret, elapsed = command([pyg, '-I', '-u', P.ROOT / 'src/prepare_data.py', ds.removeprefix('paper_')], dest / f'prepare_{ds}.log')
            if ret:
                P.S.save(dest / f'{ds}_data_error.json', dict(status='error', error=f'prepare exit {ret}; see prepare_{ds}.log'))
                print(f'FAILED DATA {ds}: exit={ret}, no model runs', flush=True)
                continue
        P.prepare(ds)
        for kib in budgets:
            for rep in range(a.reps):
                methods = ['PLBF', 'LBF', 'RA6'] if rep % 2 == 0 else ['RA6', 'LBF', 'PLBF']
                for method in methods:
                    output = dest / f'{ds}_{kib}_{method}_rep{rep}.json'
                    if output.exists():
                        print(f'SKIP existing {output.name}; no retry', flush=True)
                        continue
                    cmd = [py, '-u', P.ROOT / 'src/ra_worker.py', ds, kib, output] if method == 'RA6' else [
                        pyg, '-u', P.ROOT / 'src/original_worker.py', ds, kib, method, output]
                    print(f'START {ds} {kib}KiB {method} rep{rep}', flush=True)
                    ret, elapsed = command(cmd, output.with_suffix('.log'))
                    if output.exists():
                        row = json.loads(output.read_text())
                    else:
                        row = dict(status='error', dataset=ds, budget_kib=kib, method=method,
                                   error=f'Worker exit {ret}; see {output.with_suffix(".log").name}')
                    row.update(rep=rep, process_wall_s=elapsed)
                    P.S.save(output, row)
                    print(f'FINISH {ds} {kib}KiB {method} rep{rep}: {row["status"]} wall={elapsed:.1f}s', flush=True)
                subprocess.run([str(py), str(P.ROOT / 'src/report.py')], check=True)
    failures = [f.name for f in dest.glob('*_rep*.json') if json.loads(f.read_text())['status'] != 'ok']
    P.S.save(dest / 'completion.json', dict(finished=datetime.datetime.now().isoformat(), failures=failures,
                                          exact_paper_split=False, yelp='blocked: processed data and embeddings unavailable'))
    print(f'ALL FINISHED: {len(failures)} failed workers; Yelp/exact split unavailable', flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

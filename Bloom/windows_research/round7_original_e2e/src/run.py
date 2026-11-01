"""Run fresh-process, single-thread pairs serially. Never retry failed worker results."""
import shared as S
import argparse
import datetime
import json
import os
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--datasets', default=','.join(S.SETTINGS))
    p.add_argument('--reps', type=int, default=3)
    p.add_argument('--budget', type=int)
    p.add_argument('--suffix', default='main')
    a = p.parse_args()
    settings = [(ds, a.budget or S.SETTINGS[ds]) for ds in a.datasets.split(',')]
    dest = S.ROOT / 'results' / a.suffix
    dest.mkdir(parents=True, exist_ok=True)
    py = S.BLOOM / '.condaenv' / 'bin' / 'python'
    manifest = dest / 'manifest.json'
    config = dict(settings=settings, reps=a.reps, suffix=a.suffix)
    sources = {f.name: S.digest(f) for f in (S.ROOT / 'src').glob('*.py')}
    if manifest.exists():
        old = json.loads(manifest.read_text())
        assert old['config'] == json.loads(json.dumps(config)), 'Use a new suffix when changing the experiment'
        assert old['sources'] == sources, 'Source changed; use a new suffix rather than mixing runs'
    else:
        S.save(manifest, dict(config=config, sources=sources,
                              started=datetime.datetime.now().isoformat(), loadavg=os.getloadavg(),
                              hardware=subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True).strip(),
                              commit=subprocess.check_output(['git', '-C', str(S.BLOOM), 'rev-parse', 'HEAD'], text=True).strip()))
    for ds, kib in settings:
        subprocess.run([str(py), '-u', str(S.ROOT / 'src' / 'prepare.py'), ds], check=True)
        for rep in range(a.reps):
            methods = ['gama', 'ra6'] if rep % 2 == 0 else ['ra6', 'gama']
            for method in methods:
                output = dest / f'{ds}_{kib}_rep{rep}_{method}.json'
                if output.exists():
                    status = json.loads(output.read_text())['status']
                    if status != 'ok':
                        print(f'SKIP failed result, not retried: {output.name}', flush=True)
                        continue
                    print(f'SKIP complete {output.name}', flush=True)
                    continue
                env_py = S.BLOOM / ('.condaenv_gama' if method == 'gama' else '.condaenv') / 'bin' / 'python'
                cmd = [str(env_py), '-u', str(S.ROOT / 'src' / f'{method}_worker.py'), ds, str(kib), str(output)]
                start = time.perf_counter()
                print(f'START {ds}/{kib} rep{rep} {method}', flush=True)
                with output.with_suffix('.log').open('w') as log:
                    proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
                elapsed = time.perf_counter() - start
                print(f'FINISH {ds}/{kib} rep{rep} {method}: exit={proc.returncode} wall={elapsed:.1f}s', flush=True)
                if output.exists():
                    row = json.loads(output.read_text())
                    row.update(rep=rep, process_wall_s=elapsed, loadavg_after=os.getloadavg())
                    S.save(output, row)
                if proc.returncode != 0:
                    if not output.exists():
                        S.save(output, dict(method='Gama(original)' if method == 'gama' else 'RA6',
                                            dataset=ds, budget_kib=kib, rep=rep, status='error',
                                            error=f'Worker exit {proc.returncode}; see {output.with_suffix(".log").name}',
                                            process_wall_s=elapsed))
                    print(f'FAILED, not retried: {output.with_suffix(".log")}', flush=True)
            subprocess.run([str(py), str(S.ROOT / 'src' / 'report.py'), '--suffix', a.suffix], check=True)
    failed = sum(json.loads(f.read_text())['status'] != 'ok' for f in dest.glob('*_rep*_*.json'))
    print(f'ALL FINISHED: {failed} failed worker results', flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

"""Bounded official HTTPS data downloads; no downloaded code is executed."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import json
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ('clarknet_aug28', 'clarknet_access_log_Aug28.gz', 21756573),
    ('clarknet_sep4', 'clarknet_access_log_Sep4.gz', 20751841),
    ('sask', 'usask_access_log.gz', 30505430),
)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    tmp.replace(path)


def check_freeze():
    f = json.loads((ROOT / 'plan/download-freeze.json').read_text())
    for p, h in f['sources'].items():
        assert sha(ROOT / p) == h, p


def part(name, filename, size, i, lo, hi):
    folder = ROOT / 'inputs' / name / f'part{i}'
    folder.mkdir()
    output = folder / 'payload.part'
    headers = folder / 'headers.txt'
    start = time.perf_counter()
    url = 'https://ita.ee.lbl.gov/traces/' + filename
    run = subprocess.run([
        'curl', '--proto', '=https', '--fail', '--silent', '--show-error',
        '--connect-timeout', '20', '--max-time', '600',
        '--range', f'{lo}-{hi}', '--dump-header', str(headers),
        '--output', str(output), url,
    ], capture_output=True, text=True, cwd=ROOT)
    rec = dict(source=name, url=url, part=i, start=lo, end=hi, expected_total=size,
               exit_code=run.returncode, stderr=run.stderr, elapsed_s=time.perf_counter()-start,
               received_bytes=output.stat().st_size if output.exists() else 0)
    header = headers.read_text(errors='replace').lower() if headers.exists() else ''
    rec['range_verified'] = f'content-range: bytes {lo}-{hi}/{size}' in header
    rec['ok'] = run.returncode == 0 and rec['received_bytes'] == hi-lo+1 and rec['range_verified']
    if output.exists():
        rec['sha256'] = sha(output)
    save(ROOT / f'results/download_{name}_part{i}.json', rec)
    print('DOWNLOAD_PART', name, i, 'OK' if rec['ok'] else 'FAILED', rec['received_bytes'], flush=True)
    return rec


def main():
    check_freeze()
    assert shutil.disk_usage(ROOT).free >= 2 * 2**30, 'Require 2 GiB free disk'
    assert not (ROOT / 'results/downloads.json').exists(), 'Refuse rerun/overwrite'
    start = time.perf_counter()
    (ROOT / 'inputs').mkdir(exist_ok=True)
    for name, _, _ in FILES:
        (ROOT / 'inputs' / name).mkdir()
    futures = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, filename, size in FILES:
            step = (size + 3)//4
            for i, lo in enumerate(range(0, size, step)):
                futures.append(pool.submit(part, name, filename, size, i, lo, min(size-1,lo+step-1)))
        parts = [f.result() for f in as_completed(futures)]
    if not all(r['ok'] for r in parts):
        save(ROOT / 'results/downloads.json', dict(status='failed', parts=parts, elapsed_s=time.perf_counter()-start))
        raise RuntimeError('Download failed; partials preserved; no automatic retry')
    receipts = []
    for name, filename, size in FILES:
        folder = ROOT / 'inputs' / name / 'assembled'
        folder.mkdir()
        output = folder / filename
        with output.open('xb') as dst:
            for i in range(4):
                with (ROOT / 'inputs' / name / f'part{i}' / 'payload.part').open('rb') as src:
                    shutil.copyfileobj(src, dst, 1 << 20)
        assert output.stat().st_size == size
        check_start = time.perf_counter()
        digest = hashlib.sha256()
        expanded = 0
        with gzip.open(output, 'rb') as src:
            for block in iter(lambda: src.read(1 << 20), b''):
                expanded += len(block)
                assert expanded <= 512 * 2**20, 'Expanded data bound exceeded'
                digest.update(block)
        receipts.append(dict(name=name, path=str(output.relative_to(ROOT)), url='https://ita.ee.lbl.gov/traces/'+filename,
                             compressed_bytes=size, expanded_bytes=expanded, sha256=sha(output),
                             expanded_sha256=digest.hexdigest(), crc_verified=True, verification_s=time.perf_counter()-check_start))
        print('DOWNLOAD_VERIFIED', name, size, expanded, flush=True)
    check_freeze()
    save(ROOT / 'results/downloads.json', dict(status='complete', files=receipts, parts=parts,
                                              elapsed_s=time.perf_counter()-start))
    print('DOWNLOADS_COMPLETE', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        save(ROOT / 'results/download_failure.json', dict(status='failed', error=repr(error)))
        raise

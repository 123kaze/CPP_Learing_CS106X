"""Standard-library controls; imports never load datasets or frozen experiments."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WR = ROOT.parent
BLOOM = WR.parent
PROTOCOL = ROOT / 'plan/protocol.json'
FREEZE = ROOT / 'plan/freeze.json'
COMPLETION = WR / 'round21_shared_replay_v2/results/completion.json'
SOURCE_DIRS = (
    'windows_research/src', 'windows_research/vendor/original_src',
    'windows_research/round2_backlog/src', 'windows_research/round4_ra_plbf/src',
    'windows_research/round5_dp/src', 'windows_research/round6_bucket/src',
    'windows_research/round10_fpcache/src', 'windows_research/round11_tcp/src',
    'windows_research/round12_nomodel/src', 'windows_research/round17_zerotree/src',
    'windows_research/round19_gt_fix/src', 'windows_research/round20_zero_guard/src',
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def protocol():
    return json.loads(PROTOCOL.read_text())


def serial_gate(completion=COMPLETION, release=None):
    """Exactly one read of the prior completion file, no polling or process waits.

    Explicit coordinator release is an attestation of a failed/stopped prior run,
    not an automatic override inferred from a missing file or silence.
    """
    prior = None
    try:
        raw = Path(completion).read_bytes()
        prior = json.loads(raw)
    except FileNotFoundError:
        raw = None
    if isinstance(prior, dict) and prior.get('status') == 'complete':
        return dict(mode='completed', path=str(completion),
                    sha256=hashlib.sha256(raw).hexdigest(), record=prior)
    if release is None:
        raise RuntimeError('Serial gate closed: round21_v2 is not explicitly complete; no wait/retry performed')
    release = Path(release).resolve()
    if not release.is_relative_to(ROOT):
        raise ValueError('Coordinator release must live within round22')
    record = json.loads(release.read_text())
    if not (record.get('prior_round') == 'round21_shared_replay_v2'
            and record.get('prior_status') in ('failed', 'stopped')
            and record.get('approved_for_round22') is True
            and record.get('recorded_by') == 'coordinator'
            and record.get('reason') and record.get('prior_jobs_confirmed_stopped') is True):
        raise ValueError('Invalid explicit coordinator release')
    return dict(mode='explicit-failed-or-stopped-release', path=str(release),
                sha256=digest(release), record=record)


def freeze_sources():
    missing = [name for name in ('numpy','scipy','numba','pandas','lightgbm') if importlib.util.find_spec(name) is None]
    if missing:
        raise RuntimeError('Missing existing dependencies; no installation attempted: '+', '.join(missing))
    paths = [PROTOCOL]
    paths += sorted((ROOT / 'src').glob('*.py'))
    paths += sorted(ROOT.glob('*.txt'))
    for folder in SOURCE_DIRS:
        paths += sorted((BLOOM / folder).glob('*.py'))
    paths += [WR / 'round19_gt_fix/plan/freeze.json',
              WR / 'round21_theory_check/check_theory.py',
              WR / 'round21_theory_check/核验报告.txt']
    obj = dict(protocol=protocol()['protocol'],
               source_sha256={str(p.relative_to(BLOOM)): digest(p) for p in sorted(set(paths))})
    if FREEZE.exists():
        if json.loads(FREEZE.read_text()) != obj:
            raise RuntimeError('Prepared source freeze differs; refusing silent refreeze')
    else:
        save(FREEZE, obj)
    return obj


def verify_freeze():
    obj = json.loads(FREEZE.read_text())
    for rel, expected in obj['source_sha256'].items():
        if digest(BLOOM / rel) != expected:
            raise RuntimeError('Frozen source changed: ' + rel)
    return digest(FREEZE)


def cache_files(ds):
    folder = WR / 'round2_backlog/cache' / ds
    names = ['data.npz', 'scores.npz', 'gama_scores.npz', 'model200.txt']
    if ds.endswith('_flow'):
        names.append('trace.npy')
    return [folder / name for name in names]


def require_cached(ds):
    missing = [str(p) for p in cache_files(ds) if not p.is_file()]
    if missing:
        raise FileNotFoundError('Prepared inputs required; training forbidden: ' + ', '.join(missing))


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare', 'verify'])
    a = p.parse_args()
    if a.action == 'prepare':
        obj = freeze_sources()
        print('PREPARED ONLY', len(obj['source_sha256']), 'source hashes; no datasets loaded, no serial gate polled')
    else:
        print('FREEZE VERIFIED', verify_freeze())

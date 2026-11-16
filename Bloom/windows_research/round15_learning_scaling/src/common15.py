"""Fixed protocol and small utilities; standard-library-only imports."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WR = ROOT.parent
BLOOM = WR.parent
DATASET, KIB = 'caida', 256
LENGTHS = (1_000_000, 2_000_000, 5_000_000, 10_000_000, 20_000_000, 50_000_000, 100_000_000)
REPS = 3
CHUNK = 1_000_000
PERM_SEED, STREAM_SEED = 15001, 15002
PILOT_L = 100_000


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def array_hash(a):
    return hashlib.sha256(memoryview(a).cast('B')).hexdigest()

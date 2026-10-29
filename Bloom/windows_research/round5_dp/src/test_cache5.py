"""Tests for cache5: 2^q equivalence with round-2 fast_cache, zero false negatives, utilization."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'round2_backlog' / 'src'))
import engine as E  # noqa: E402
import cache5 as K  # noqa: E402

setup, scores, safe = E.load('cod')
F = E.F
rng = np.random.default_rng(7)
zeros = [c for c in (E.build(setup, scores, t, 256, 0.) for t in (8, 48)) if c]
fp = zeros[0]['structure'].fp_static
pool = np.flatnonzero(fp)[:20000]
stream = np.concatenate([pool[rng.integers(0, len(pool), 300000)], rng.integers(0, len(setup.h1q), 300000)])
rng.shuffle(stream)
# 1. equivalence at power-of-two bucket counts
for q in (4, 8, 11, 14):
    spec = K.layout_with_buckets(1 << q)
    old = F.layout(spec['allocated_bytes'], 40, 'clock', 4)
    assert old['buckets'] == 1 << q and old['allocated_bytes'] == spec['allocated_bytes'], (q, old, spec)
    a = F.simulate(stream, setup.h1q, safe, fp, spec['allocated_bytes'])
    data = K.allocate(spec)
    res = K.replay(stream, setup.h1q, safe, fp, data, spec['buckets'], 40, spec['Q'], spec['ob'], spec['slot_bits'],
                   4, spec['handbits'], 2 ** 62, np.zeros(0, np.int64), np.zeros(0, np.bool_))
    keys = ['fp', 'hits', 'inserts', 'evictions', 'bypasses']
    assert [a[k] for k in keys] == list(res[:5]), (q, [a[k] for k in keys], res[:5])
    print(f'2^{q} buckets: identical to round-2 cache', dict(zip(keys, res[:5])))
# 2. zero false negatives with arbitrary bucket counts (and other prefix lengths / ways)
for B, P, W in ((1, 40, 4), (97, 40, 4), (1000, 40, 4), (12345, 40, 4), (3001, 24, 4), (3001, 48, 4), (777, 40, 1), (777, 40, 8)):
    spec = K.layout_with_buckets(B, P, W)
    data = K.allocate(spec)
    res = K.replay(stream, setup.h1q, safe, fp, data, B, P, spec['Q'], spec['ob'], spec['slot_bits'], W,
                   spec['handbits'], 2 ** 62, np.zeros(0, np.int64), np.zeros(0, np.bool_))
    bad = K.count_member_hits(data, setup.h1m, B, P, spec['Q'], spec['ob'], spec['slot_bits'], W)
    assert bad == 0, (B, P, W, bad)
    print(f'B={B} P={P} ways={W}: inserts={res[2]} hits={res[1]} member hits={bad}')
# 3. utilization
worst = min(K.layout(b)['allocated_bytes'] / b for b in np.unique(np.geomspace(2000, 4e6, 400).astype(int)))
print('worst allocated/reserved over 2KB..4MB:', round(worst, 4))
assert worst >= 0.95
print('ALL CACHE5 TESTS PASSED')

"""Checks for cache_fp.  run: ../../.condaenv/bin/python src/test_cache_fp.py
1. With F = P = 40 and every safe length = 40 the frozen cache5 matches exactly the same 40 bits,
   so for the same bucket count every counter must be identical (only the record layout differs).
2. Byte accounting: the allocated array never exceeds the budget, and 64-bit records hold fewer slots.
3. False negatives: no member collides with a cached 64-bit fingerprint on a random workload.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cache_fp as F  # noqa: E402

C5 = F.C5
rng = np.random.default_rng(7)
n = 200_000
hashes = rng.integers(0, 2 ** 63, n, dtype=np.int64).astype(np.uint64) * np.uint64(2) + rng.integers(0, 2, n).astype(np.uint64)
fp = rng.random(n) < .3
stream = (rng.zipf(1.2, 2_000_000) - 1) % n

for B in (1, 7, 1000, 4096, 12345):
    s5 = C5.layout_with_buckets(B, 40, 4)
    d5 = C5.allocate(s5)
    r5 = C5.replay(stream, hashes, np.full(n, 40, np.int64), fp, d5, B, 40, s5['Q'], s5['ob'], s5['slot_bits'], 4,
                   s5['handbits'], 2 ** 62, np.zeros(0, np.int64), np.zeros(0, np.bool_))
    alloc, sb = F._bytes(B, 40, 4)
    sf = dict(buckets=B, slots=4 * B, slot_bits=sb, allocated_bytes=alloc, budget_bytes=alloc, prefix_bits=40,
              ways=4, Q=32, ob=F._ob(B, 32), handbits=2, nwords=(alloc - F.ARRAY_HEADER) // 8)
    df = F.allocate(sf)
    rf = F.replay(stream, hashes, np.zeros(0, np.bool_), fp, df, B, 40, 32, sf['ob'], sb, 4, 2, 2 ** 62,
                  np.zeros(0, np.int64), np.zeros(0, np.bool_))
    assert (r5 == rf[:8]).all(), (B, r5, rf)
print('1. identical to cache5 with F = P = 40 and safe = 40: ok')

for budget in (100, 1000, 65536, 10 ** 6):
    a, b = F.layout(budget), C5.layout(budget, 40, 4)
    assert a['allocated_bytes'] <= budget and (a['slots'] == 0 or a['slots'] < b['slots'] or b['slots'] == 0)
    print(f'   {budget} B: cache5 slots {b["slots"]}, 64-bit fingerprint slots {a["slots"]}')
print('2. byte accounting: ok')

members = rng.integers(0, 2 ** 63, 1_000_000, dtype=np.int64).astype(np.uint64) * np.uint64(2)
r = F.simulate(stream, hashes, None, fp, 10 ** 6, member_hashes=members)
assert r['member_hits_final'] == 0 and r['bypasses'] == 0
print('3. no false negative on 1M random members:', r['fp'], 'FPs', r['hits'], 'hits')

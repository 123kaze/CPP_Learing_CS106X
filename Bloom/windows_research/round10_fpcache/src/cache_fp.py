"""Index-free negative cache: F-bit hash fingerprints, no member hash index.

Round 5's cache (round5_dp/src/cache5.py) stores, for every cached false positive, its P = 40-bit
hash prefix plus the shortest prefix length that no member shares ("safe length").  Computing
that length needs a sorted index of all member hashes (8 B per member), which is outside the
filter budget.  This variant drops the index: a slot stores the key's top F hash bits and a hit
needs all F bits to match.  Everything else is cache5 unchanged: the same multiply-shift bucket
of the top Q = 32 bits (so the bucket of every key, and RA6's bucket-load prediction, are the
same), 4-way CLOCK per bucket, the same word-packed array and header, same byte accounting.
Record: [offset ob][low F-Q][valid 1][reference 1]  (no 6-bit length field).

Cost: a member whose top F hash bits equal a cached false positive's is answered "negative"
(a false negative).  Per member query the probability is at most (occupied slots) * 2^-F
(F = 64: below 1e-13 for every cache size used here); count_member_hits measures it exactly
on the final cache state.  Every insert succeeds (no bypass), and a cached prefix no longer
covers other keys that share a shorter safe prefix.
"""
import sys
import numpy as np
from numba import njit

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'round5_dp' / 'src'))
import cache5 as C5  # noqa: E402  (frozen round 5: bit get/put, header size)

FP_BITS = 64
HEAD = C5.HEAD
ARRAY_HEADER = C5.ARRAY_HEADER
get, put = C5.get, C5.put


def _ob(B, Q):
    return C5._ob(B, Q)


def _bytes(B, F, ways):
    Q = min(F, 32)
    sb = _ob(B, Q) + (F - Q) + 2
    hb = int(np.log2(ways))
    words = HEAD + (B * ways * sb + B * hb + 63) // 64
    return words * 8 + ARRAY_HEADER, sb


def layout(budget_bytes, prefix_bits=None, ways=4, F=None):
    """Largest bucket count whose packed array fits `budget_bytes` (prefix_bits is ignored:
    the engine passes its own P = 40; the fingerprint length is F)."""
    F = F or FP_BITS
    assert ways in (1, 2, 4, 8) and 32 <= F <= 64
    Q = min(F, 32)
    out = dict(buckets=0, slots=0, slot_bits=0, allocated_bytes=0, budget_bytes=int(budget_bytes),
               prefix_bits=F, ways=ways, Q=Q, ob=0, handbits=int(np.log2(ways)), nwords=0)
    if budget_bytes < _bytes(1, F, ways)[0]:
        return out
    lo, hi = 1, 1 << 31
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if _bytes(mid, F, ways)[0] <= budget_bytes:
            lo = mid
        else:
            hi = mid
    alloc, sb = _bytes(lo, F, ways)
    out.update(buckets=lo, slots=lo * ways, slot_bits=sb, allocated_bytes=alloc, ob=_ob(lo, Q),
               nwords=(alloc - ARRAY_HEADER) // 8)
    return out


allocate = C5.allocate


@njit(cache=True, inline='always')
def _split(h, B, F, Q):
    """bucket, offset in bucket, low F-Q bits, of hash h (as cache5._split with P = F)."""
    h = np.uint64(h)
    x = h >> np.uint64(64 - Q)
    b = np.int64((x * np.uint64(B)) >> np.uint64(Q))
    start = ((np.uint64(b) << np.uint64(Q)) + np.uint64(B) - np.uint64(1)) // np.uint64(B)
    o = x - start
    low = np.uint64(0)
    if F > Q:
        low = (h >> np.uint64(64 - F)) & (np.uint64(0xFFFFFFFFFFFFFFFF) >> np.uint64(64 - (F - Q)))
    return b, o, low


@njit(cache=True)
def lookup(data, h, B, F, Q, ob, sb, ways):
    if B == 0:
        return False
    b, o, low = _split(h, B, F, Q)
    for way in range(ways):
        rec = 256 + (b * ways + way) * sb
        if get(data, rec + ob + (F - Q), 1) == 0:
            continue
        if get(data, rec, ob) == o and get(data, rec + ob, F - Q) == low:
            put(data, rec + ob + (F - Q) + 1, 1, np.uint64(1))
            return True
    return False


@njit(cache=True)
def insert(data, h, B, F, Q, ob, sb, ways, hb):
    """1 = inserted into a free slot, 2 = inserted with eviction (CLOCK, as cache5.insert)."""
    if B == 0:
        return 0
    b, o, low = _split(h, B, F, Q)
    first = b * ways
    choice = -1
    for w in range(ways):
        if get(data, 256 + (first + w) * sb + ob + (F - Q), 1) == 0:
            choice = w
            break
    evicted = choice == -1
    hp = 256 + B * ways * sb + b * hb
    if choice == -1:
        hand = np.int64(get(data, hp, hb))
        for _ in range(ways * 2):
            rec = 256 + (first + hand) * sb
            if get(data, rec + ob + (F - Q) + 1, 1) == 0:
                choice = hand
                break
            put(data, rec + ob + (F - Q) + 1, 1, np.uint64(0))
            hand = (hand + 1) % ways
        if choice == -1:
            choice = hand
        put(data, hp, hb, np.uint64((choice + 1) % ways))
    rec = 256 + (first + choice) * sb
    put(data, rec, ob, o)
    put(data, rec + ob, F - Q, low)
    put(data, rec + ob + (F - Q), 1, np.uint64(1))
    put(data, rec + ob + (F - Q) + 1, 1, np.uint64(1))
    return 2 if evicted else 1


@njit(cache=True)
def replay(stream, hashes, member, fp, data, B, F, Q, ob, sb, ways, hb, limit, miss, fp_seen):
    # counts: FP, hits, inserts, evictions, bypasses, processed, cutoff, occupied, false negatives
    counts = np.zeros(9, np.int64)
    for i in range(len(stream)):
        x = np.int64(stream[i])
        h = hashes[x]
        if lookup(data, h, B, F, Q, ob, sb, ways):
            counts[1] += 1
            if len(member) and member[x]:
                counts[8] += 1
        elif fp[x]:
            counts[0] += 1
            if len(miss):
                miss[x] += 1
            if len(fp_seen):
                fp_seen[x] = True
            if counts[0] > limit:
                counts[5] = i + 1
                counts[6] = 1
                return counts
            outcome = insert(data, h, B, F, Q, ob, sb, ways, hb)
            if outcome:
                counts[2] += 1
                if outcome == 2:
                    counts[3] += 1
                else:
                    counts[7] += 1
        counts[5] += 1
    return counts


@njit(cache=True)
def count_member_hits(data, member_hashes, B, F, Q, ob, sb, ways):
    """Members the final cache would answer 'cached negative' for (false negatives)."""
    n = 0
    for i in range(len(member_hashes)):
        if lookup(data, member_hashes[i], B, F, Q, ob, sb, ways):
            n += 1
    return n


def simulate(stream, hashes, safe, fp, cache_bytes, prefix_bits=None, ways=4, limit=2 ** 62,
             collect=False, per_key=False, member_hashes=None, F=None):
    """Same signature and result keys as cache5.simulate; `safe` (the member-index output) is
    ignored.  With member_hashes, also reports how many members the final cache would hit."""
    spec = layout(cache_bytes, None, ways, F)
    data = allocate(spec)
    miss = np.zeros(len(hashes) if per_key else 0, np.int64)
    seen = np.zeros(len(hashes) if collect else 0, np.bool_)
    res = replay(np.asarray(stream, np.int64), hashes, np.zeros(0, np.bool_), fp, data, spec['buckets'],
                 spec['prefix_bits'], spec['Q'], spec['ob'], spec['slot_bits'], ways, spec['handbits'],
                 int(limit), miss, seen)
    names = ['fp', 'hits', 'inserts', 'evictions', 'bypasses', 'processed', 'cutoff', 'occupied']
    out = {k: int(v) for k, v in zip(names, res[:8])}
    out.update(spec)
    out['distinct_fp_keys'] = int(seen.sum()) if collect else None
    if per_key:
        out['miss'] = miss
    if member_hashes is not None:
        out['member_hits_final'] = int(count_member_hits(data, np.asarray(member_hashes, np.uint64), spec['buckets'],
                                                         spec['prefix_bits'], spec['Q'], spec['ob'],
                                                         spec['slot_bits'], ways)) if spec['buckets'] else 0
    return out

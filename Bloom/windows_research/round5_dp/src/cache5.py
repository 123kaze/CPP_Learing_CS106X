"""F-B: word-packed verified-prefix CLOCK cache with an arbitrary number of buckets.

Round 2's cache (fast_cache.py) needs 2^q buckets, so up to half of a cache reservation was
returned unused.  Here the bucket of a key is a multiply-shift range reduction of its top
Q = min(P, 32) hash bits, b = (x * B) >> Q, for any B.  A slot stores x's offset inside its
bucket (x - start(b), start(b) = ceil(b * 2^Q / B)) and the next P - Q hash bits, so the full
P-bit prefix of the stored key is recovered exactly and compared on the stored safe length L:
no member can ever match (zero false negatives), exactly as in round 2.
Record: [offset ob][low P-Q][length 6][valid 1][reference 1]; per bucket a CLOCK hand.
With B = 2^q the layout, bytes and every hit/miss equal round 2's fast_cache bit for bit.
"""
import sys
import numpy as np
from numba import njit

HEAD = 4
ARRAY_HEADER = sys.getsizeof(np.empty(0, np.uint64))


def _ob(B, Q):
    span = -(-(1 << Q) // B)           # ceil(2^Q / B): largest number of x values in one bucket
    return max(1, (span - 1).bit_length())


def _bytes(B, P, ways):
    Q = min(P, 32)
    sb = _ob(B, Q) + (P - Q) + 8
    hb = int(np.log2(ways))
    words = HEAD + (B * ways * sb + B * hb + 63) // 64
    return words * 8 + ARRAY_HEADER, sb


def layout(budget_bytes, prefix_bits=40, ways=4):
    """Largest bucket count whose packed array fits `budget_bytes`."""
    assert ways in (1, 2, 4, 8) and 16 <= prefix_bits <= 56
    Q = min(prefix_bits, 32)
    out = dict(buckets=0, slots=0, slot_bits=0, allocated_bytes=0, budget_bytes=int(budget_bytes),
               prefix_bits=prefix_bits, ways=ways, Q=Q, ob=0, handbits=int(np.log2(ways)), nwords=0)
    if budget_bytes < _bytes(1, prefix_bits, ways)[0]:
        return out
    lo, hi = 1, 1 << 31
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if _bytes(mid, prefix_bits, ways)[0] <= budget_bytes:
            lo = mid
        else:
            hi = mid
    alloc, sb = _bytes(lo, prefix_bits, ways)
    out.update(buckets=lo, slots=lo * ways, slot_bits=sb, allocated_bytes=alloc, ob=_ob(lo, Q),
               nwords=(alloc - ARRAY_HEADER) // 8)
    return out


def allocate(spec):
    data = np.zeros(spec['nwords'], np.uint64)
    if spec['nwords']:
        assert sys.getsizeof(data) == spec['allocated_bytes'] <= spec['budget_bytes']
        data[1] = np.uint64(spec['buckets'])
        data[2] = np.uint64(spec['slots'])
    return data


@njit(cache=True, inline='always')
def get(data, bit, width):
    if width == 0:
        return np.uint64(0)
    word = bit >> 6
    shift = bit & 63
    value = data[word] >> np.uint64(shift)
    if shift + width > 64:
        value |= data[word + 1] << np.uint64(64 - shift)
    return value & (np.uint64(0xFFFFFFFFFFFFFFFF) >> np.uint64(64 - width))


@njit(cache=True, inline='always')
def put(data, bit, width, value):
    if width == 0:
        return
    word = bit >> 6
    shift = bit & 63
    mask = np.uint64(0xFFFFFFFFFFFFFFFF) >> np.uint64(64 - width)
    value = np.uint64(value) & mask
    data[word] = (data[word] & ~(mask << np.uint64(shift))) | (value << np.uint64(shift))
    if shift + width > 64:
        high = shift + width - 64
        highmask = np.uint64(0xFFFFFFFFFFFFFFFF) >> np.uint64(64 - high)
        data[word + 1] = (data[word + 1] & ~highmask) | (value >> np.uint64(64 - shift))


@njit(cache=True, inline='always')
def _split(h, B, P, Q):
    """bucket, offset in bucket, low bits, full P-bit prefix of hash h."""
    h = np.uint64(h)
    x = h >> np.uint64(64 - Q)
    b = np.int64((x * np.uint64(B)) >> np.uint64(Q))
    start = (np.uint64(b) << np.uint64(Q)) + np.uint64(B) - np.uint64(1)
    start = start // np.uint64(B)
    o = x - start
    low = np.uint64(0)
    if P > Q:
        low = (h >> np.uint64(64 - P)) & ((np.uint64(1) << np.uint64(P - Q)) - np.uint64(1))
    prefix = h >> np.uint64(64 - P)
    return b, o, low, prefix, start


@njit(cache=True)
def lookup(data, h, B, P, Q, ob, sb, ways):
    if B == 0:
        return False
    b, o, low, prefix, start = _split(h, B, P, Q)
    for way in range(ways):
        rec = 256 + (b * ways + way) * sb
        if get(data, rec + ob + (P - Q) + 6, 1) == 0:
            continue
        so = get(data, rec, ob)
        sl = get(data, rec + ob, P - Q)
        length = np.int64(get(data, rec + ob + (P - Q), 6))
        stored = ((start + so) << np.uint64(P - Q)) | sl
        if (stored >> np.uint64(P - length)) == (prefix >> np.uint64(P - length)):
            put(data, rec + ob + (P - Q) + 7, 1, np.uint64(1))
            return True
    return False


@njit(cache=True)
def insert(data, h, length, B, P, Q, ob, sb, ways, hb):
    """0 = bypass (no safe prefix within P bits), 1 = inserted, 2 = inserted with eviction."""
    if B == 0 or length > P or length >= 64:
        return 0
    b, o, low, prefix, start = _split(h, B, P, Q)
    first = b * ways
    choice = -1
    for w in range(ways):
        if get(data, 256 + (first + w) * sb + ob + (P - Q) + 6, 1) == 0:
            choice = w
            break
    evicted = choice == -1
    hp = 256 + B * ways * sb + b * hb
    if choice == -1:
        hand = np.int64(get(data, hp, hb))
        for _ in range(ways * 2):
            rec = 256 + (first + hand) * sb
            if get(data, rec + ob + (P - Q) + 7, 1) == 0:
                choice = hand
                break
            put(data, rec + ob + (P - Q) + 7, 1, np.uint64(0))
            hand = (hand + 1) % ways
        if choice == -1:
            choice = hand
        put(data, hp, hb, np.uint64((choice + 1) % ways))
    rec = 256 + (first + choice) * sb
    put(data, rec, ob, o)
    put(data, rec + ob, P - Q, low)
    put(data, rec + ob + (P - Q), 6, np.uint64(length))
    put(data, rec + ob + (P - Q) + 6, 1, np.uint64(1))
    put(data, rec + ob + (P - Q) + 7, 1, np.uint64(1))
    return 2 if evicted else 1


@njit(cache=True)
def replay(stream, hashes, safe, fp, data, B, P, Q, ob, sb, ways, hb, limit, miss, fp_seen):
    # counts: FP, hits, inserts, evictions, bypasses, processed, cutoff, occupied
    counts = np.zeros(8, np.int64)
    for i in range(len(stream)):
        x = np.int64(stream[i])
        h = hashes[x]
        if lookup(data, h, B, P, Q, ob, sb, ways):
            counts[1] += 1
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
            outcome = insert(data, h, safe[x], B, P, Q, ob, sb, ways, hb)
            if outcome:
                counts[2] += 1
                if outcome == 2:
                    counts[3] += 1
                else:
                    counts[7] += 1
            else:
                counts[4] += 1
        counts[5] += 1
    return counts


def simulate(stream, hashes, safe, fp, cache_bytes, prefix_bits=40, ways=4, limit=2 ** 62,
             collect=False, per_key=False):
    spec = layout(cache_bytes, prefix_bits, ways)
    data = allocate(spec)
    miss = np.zeros(len(hashes) if per_key else 0, np.int64)
    seen = np.zeros(len(hashes) if collect else 0, np.bool_)
    res = replay(np.asarray(stream, np.int64), hashes, safe, fp, data, spec['buckets'], prefix_bits, spec['Q'],
                 spec['ob'], spec['slot_bits'], ways, spec['handbits'], int(limit), miss, seen)
    names = ['fp', 'hits', 'inserts', 'evictions', 'bypasses', 'processed', 'cutoff', 'occupied']
    out = {k: int(v) for k, v in zip(names, res)}
    out.update(spec)
    out['distinct_fp_keys'] = int(seen.sum()) if collect else None
    if per_key:
        out['miss'] = miss
    return out


def layout_with_buckets(B, prefix_bits=40, ways=4):
    """Layout for an explicit bucket count (tests and the 2^q equivalence check)."""
    alloc, sb = _bytes(B, prefix_bits, ways)
    Q = min(prefix_bits, 32)
    return dict(buckets=B, slots=B * ways, slot_bits=sb, allocated_bytes=alloc, budget_bytes=alloc,
                prefix_bits=prefix_bits, ways=ways, Q=Q, ob=_ob(B, Q), handbits=int(np.log2(ways)),
                nwords=(alloc - ARRAY_HEADER) // 8)


@njit(cache=True)
def count_member_hits(data, member_hashes, B, P, Q, ob, sb, ways):
    """Number of members the cache would wrongly answer 'cached negative' for (must be 0)."""
    n = 0
    for i in range(len(member_hashes)):
        if lookup(data, member_hashes[i], B, P, Q, ob, sb, ways):
            n += 1
    return n

"""A measured, bit-packed, four-way quotient negative cache.

This is a SET-ASSOCIATIVE cache, not a shifting quotient filter. Bucket index
bits are implicit. Every slot reserves the maximum remainder width, while a
six-bit field records the actual safe prefix length. CLOCK uses one reference
bit per slot and a packed two-bit hand per bucket. The optional ``lru`` policy
is exact LRU WITHIN EACH BUCKET, using charged uint64 logical timestamps; it is
not global LRU. Prefixes exceeding the fixed maximum are safely bypassed.

The sole persistent cache allocation is an owning uint8 ndarray. Its measured
Python ndarray header, the 32-byte packed format header, all empty slots and
replacement metadata are charged. Caller-owned query arrays, sorted membership
index, model and BF are outside this component and must be charged separately
where applicable. No claim is made that a Python process RSS fits this budget.
"""

import sys

import numpy as np
from numba import njit

HEADER_BYTES = 32
ARRAY_HEADER_BYTES = sys.getsizeof(np.empty(0, dtype=np.uint8))
WAYS = 4


def layout(budget_bytes, prefix_bits=40, policy="clock", ways=WAYS):
    """Return the largest power-of-two bucket layout fitting real allocation.

    prefix_bits is fixed before experiments, not selected using query results.
    ``allocated_bytes`` equals sys.getsizeof(the owning slab) on this runtime.
    A zero-capacity cache allocates nothing and bypasses all operations.
    """
    if ways != WAYS:
        raise ValueError("This implementation uses exactly four ways")
    if policy not in ("clock", "lru", "bucket_lru"):
        raise ValueError("policy must be clock or lru (bucket-local LRU)")
    if not 2 <= prefix_bits <= 64:
        raise ValueError("prefix_bits must be between 2 and 64")
    budget = max(0, int(budget_bytes))
    code = 0 if policy == "clock" else 1
    best = None
    for q in range(1, min(prefix_bits, 40)):
        r = prefix_bits - q
        sbits = r + 6 + 1 + (1 if code == 0 else 64)
        buckets = 1 << q
        slots = buckets * WAYS
        hand_bits = buckets * 2 if code == 0 else 0
        slab = HEADER_BYTES + (slots * sbits + hand_bits + 7) // 8
        allocated = slab + ARRAY_HEADER_BYTES
        if allocated <= budget:
            best = dict(qbits=q, rbits=r, slot_bits=sbits, policy_code=code,
                        buckets=buckets, slots=slots, slab_bytes=slab,
                        allocated_bytes=allocated, payload_bytes=slab - HEADER_BYTES,
                        ndarray_header_bytes=ARRAY_HEADER_BYTES,
                        format_header_bytes=HEADER_BYTES, prefix_bits=prefix_bits,
                        policy="clock" if code == 0 else "bucket_lru",
                        max_occupancy_bits_per_slot=allocated * 8 / slots,
                        budget_bytes=budget)
        elif q > 1:
            break
    if best is None:
        return dict(qbits=0, rbits=0, slot_bits=0, policy_code=code,
                    buckets=0, slots=0, slab_bytes=0, allocated_bytes=0,
                    payload_bytes=0, ndarray_header_bytes=0, format_header_bytes=0,
                    prefix_bits=prefix_bits,
                    policy="clock" if code == 0 else "bucket_lru",
                    max_occupancy_bits_per_slot=0.0, budget_bytes=budget)
    return best


def allocate(layout_info):
    """Create the one owning allocation; assert the accounting on this runtime."""
    if not layout_info["slots"]:
        return np.empty(0, dtype=np.uint8)
    slab = np.zeros(layout_info["slab_bytes"], dtype=np.uint8)
    assert sys.getsizeof(slab) == layout_info["allocated_bytes"]
    assert sys.getsizeof(slab) <= layout_info["budget_bytes"]
    # Header[0:8] is a uint64 query/insert clock. Persist the structural metadata
    # in the charged format header, rather than leaving it in an uncharged map.
    slab[8:12] = [layout_info["qbits"], layout_info["rbits"],
                  layout_info["slot_bits"], layout_info["policy_code"]]
    slab[12] = WAYS
    slab[13] = layout_info["prefix_bits"]
    return slab


@njit(cache=True, inline="always")
def _get(data, bit, width):
    out = np.uint64(0)
    done = 0
    while done < width:
        pos = bit + done
        shift = pos & 7
        take = min(8 - shift, width - done)
        chunk = (np.uint64(data[pos >> 3]) >> np.uint64(shift)) & np.uint64((1 << take) - 1)
        out |= chunk << np.uint64(done)
        done += take
    return out


@njit(cache=True, inline="always")
def _set(data, bit, width, value):
    v = np.uint64(value)
    done = 0
    while done < width:
        pos = bit + done
        shift = pos & 7
        take = min(8 - shift, width - done)
        mask = ((1 << take) - 1) << shift
        old = int(data[pos >> 3])
        chunk = int((v >> np.uint64(done)) & np.uint64((1 << take) - 1)) << shift
        data[pos >> 3] = np.uint8((old & (255 ^ mask)) | chunk)
        done += take


@njit(cache=True, inline="always")
def _record(slot, slot_bits):
    return HEADER_BYTES * 8 + slot * slot_bits


@njit(cache=True, inline="always")
def _tick(data):
    t = _get(data, 0, 64) + np.uint64(1)
    _set(data, 0, 64, t)
    return t


@njit(cache=True)
def common_prefix_length(a, b):
    z = np.uint64(a) ^ np.uint64(b)
    n = 0
    if z == 0:
        return 64
    while (z & np.uint64(0x8000000000000000)) == 0:
        n += 1
        z <<= np.uint64(1)
    return n


@njit(cache=True)
def safe_prefix_length(sorted_member_hashes, h):
    """Shortest distinguishing prefix; 65 means an exact member-hash collision."""
    h = np.uint64(h)
    lo, hi = 0, sorted_member_hashes.size
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_member_hashes[mid] < h:
            lo = mid + 1
        else:
            hi = mid
    longest = -1
    if lo < sorted_member_hashes.size:
        longest = common_prefix_length(sorted_member_hashes[lo], h)
    if lo > 0:
        longest = max(longest, common_prefix_length(sorted_member_hashes[lo - 1], h))
    return longest + 1


@njit(cache=True)
def safe_prefix_lengths(sorted_member_hashes, hashes):
    out = np.empty(hashes.size, np.int16)
    for i in range(hashes.size):
        out[i] = safe_prefix_length(sorted_member_hashes, hashes[i])
    return out


@njit(cache=True)
def cache_lookup(slab, h, qbits, rbits, slot_bits, policy_code):
    """Probe an actual prefix and update CLOCK reference or bucket-LRU time."""
    if qbits == 0:
        return False
    h = np.uint64(h)
    bucket = np.int64(h >> np.uint64(64 - qbits))
    remainder = (h >> np.uint64(64 - qbits - rbits)) & ((np.uint64(1) << np.uint64(rbits)) - np.uint64(1))
    for way in range(WAYS):
        rec = _record(bucket * WAYS + way, slot_bits)
        if _get(slab, rec + rbits + 6, 1) == 0:
            continue
        length = np.int64(_get(slab, rec + rbits, 6))
        stored = _get(slab, rec, rbits)
        if (stored >> np.uint64(rbits - length)) == (remainder >> np.uint64(rbits - length)):
            if policy_code == 0:
                _set(slab, rec + rbits + 7, 1, np.uint64(1))
            else:
                _set(slab, rec + rbits + 7, 64, _tick(slab))
            return True
    return False


@njit(cache=True)
def cache_insert(slab, h, safe_length, qbits, rbits, slot_bits, policy_code):
    """Insert a membership-verified prefix, returning 0=bypass,1=new,2=evict.

    Call only after cache_lookup missed and authoritative backend rejected key.
    A safe_length of 65 (member/full-hash collision) is always bypassed.
    """
    if qbits == 0 or safe_length > qbits + rbits or safe_length >= 65:
        return 0
    h = np.uint64(h)
    bucket = np.int64(h >> np.uint64(64 - qbits))
    first = bucket * WAYS
    chosen = -1
    for way in range(WAYS):
        rec = _record(first + way, slot_bits)
        if _get(slab, rec + rbits + 6, 1) == 0:
            chosen = way
            break
    evicted = chosen == -1
    if chosen == -1 and policy_code == 0:
        hand_bit = HEADER_BYTES * 8 + (1 << qbits) * WAYS * slot_bits + bucket * 2
        hand = np.int64(_get(slab, hand_bit, 2))
        for _ in range(WAYS * 2):
            rec = _record(first + hand, slot_bits)
            if _get(slab, rec + rbits + 7, 1) == 0:
                chosen = hand
                break
            _set(slab, rec + rbits + 7, 1, np.uint64(0))
            hand = (hand + 1) % WAYS
        _set(slab, hand_bit, 2, np.uint64((chosen + 1) % WAYS))
    elif chosen == -1:
        oldest = np.uint64(0xFFFFFFFFFFFFFFFF)
        for way in range(WAYS):
            rec = _record(first + way, slot_bits)
            stamp = _get(slab, rec + rbits + 7, 64)
            if stamp <= oldest:
                oldest = stamp
                chosen = way
    rec = _record(first + chosen, slot_bits)
    remainder = (h >> np.uint64(64 - qbits - rbits)) & ((np.uint64(1) << np.uint64(rbits)) - np.uint64(1))
    _set(slab, rec, rbits, remainder)
    _set(slab, rec + rbits, 6, np.uint64(max(0, safe_length - qbits)))
    _set(slab, rec + rbits + 6, 1, np.uint64(1))
    if policy_code == 0:
        _set(slab, rec + rbits + 7, 1, np.uint64(1))
    else:
        _set(slab, rec + rbits + 7, 64, _tick(slab))
    return 2 if evicted else 1


@njit(cache=True)
def invalidate_for_member(slab, member_h, qbits, rbits, slot_bits):
    """Before publishing a new member, invalidate every colliding cached prefix.

    This supports safe member insertion by invalidation, not prefix extension;
    length extension needs the original negative key, which this cache omits.
    Caller must then update its authoritative membership index atomically.
    """
    if qbits == 0:
        return 0
    h = np.uint64(member_h)
    bucket = np.int64(h >> np.uint64(64 - qbits))
    remainder = (h >> np.uint64(64 - qbits - rbits)) & ((np.uint64(1) << np.uint64(rbits)) - np.uint64(1))
    removed = 0
    for way in range(WAYS):
        rec = _record(bucket * WAYS + way, slot_bits)
        if _get(slab, rec + rbits + 6, 1) == 0:
            continue
        length = np.int64(_get(slab, rec + rbits, 6))
        stored = _get(slab, rec, rbits)
        if (stored >> np.uint64(rbits - length)) == (remainder >> np.uint64(rbits - length)):
            _set(slab, rec + rbits + 6, 1, np.uint64(0))
            removed += 1
    return removed


@njit(cache=True)
def _simulate(stream, hashes, safe_lengths, fp_static, slab, tail_start,
              qbits, rbits, slot_bits, policy_code):
    # full FP, tail FP, full hit, tail hit, insert, evict, bypass, final occupied
    counts = np.zeros(8, dtype=np.int64)
    for i in range(stream.size):
        x = int(stream[i])
        hit = cache_lookup(slab, hashes[x], qbits, rbits, slot_bits, policy_code)
        if hit:
            counts[2] += 1
            if i >= tail_start:
                counts[3] += 1
        elif fp_static[x]:
            counts[0] += 1
            if i >= tail_start:
                counts[1] += 1
            outcome = cache_insert(slab, hashes[x], int(safe_lengths[x]), qbits, rbits, slot_bits, policy_code)
            if outcome:
                counts[4] += 1
                if outcome == 2:
                    counts[5] += 1
                else:
                    counts[7] += 1
            else:
                counts[6] += 1
    return counts


def simulate(stream, hashes, safe_lengths, fp_static, cache_bytes, tail_start=0,
             policy="clock", prefix_bits=40):
    """Replay negative queries using actual packed prefix lookup and replacement."""
    spec = layout(cache_bytes, prefix_bits, policy)
    slab = allocate(spec)
    result = _simulate(np.asarray(stream, dtype=np.int64),
                       np.asarray(hashes, dtype=np.uint64),
                       np.asarray(safe_lengths, dtype=np.int16),
                       np.asarray(fp_static, dtype=np.bool_), slab, int(tail_start),
                       spec["qbits"], spec["rbits"], spec["slot_bits"], spec["policy_code"])
    names = ("fp_full", "fp_tail", "hits_full", "hits_tail", "inserts", "evictions", "bypasses", "occupied")
    out = {k: int(v) for k, v in zip(names, result)}
    out.update(spec)
    out["actual_bits_per_occupied"] = spec["allocated_bytes"] * 8 / max(1, out["occupied"])
    return out


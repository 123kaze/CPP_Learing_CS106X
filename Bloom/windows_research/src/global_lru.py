"""Exact GLOBAL LRU with fully charged full-hash lookup and recency metadata.

One owning packed ndarray holds a 32-byte header, 16-byte records (uint64 key,
uint32 previous/next), and a uint32 open-addressing table. Empty slots and the
owning ndarray's Python header are included. Backward-shift deletion prevents
tombstone accumulation. Zero is an index sentinel, not a hash sentinel.
Cached full hashes must first be checked against the authoritative member set;
safe_lengths >=65 are therefore bypassed. Member insertion requires cache
invalidation before that member is published, as with the prefix backend.
"""
import sys
import numpy as np
from numba import njit
from compact_cache import _get, _set, ARRAY_HEADER_BYTES

HEADER_BYTES = 32
ENTRY_BYTES = 16


def layout(budget_bytes, prefix_bits=64, policy="lru", ways=None):
    budget = max(0, int(budget_bytes))
    best = None
    for p in range(1, 32):
        table_slots = 1 << p
        capacity = min(int(table_slots * .7),
                       max(0, (budget - ARRAY_HEADER_BYTES - HEADER_BYTES - table_slots * 4) // ENTRY_BYTES))
        if capacity < 1:
            if table_slots * 4 + HEADER_BYTES + ARRAY_HEADER_BYTES > budget:
                break
            continue
        slab = HEADER_BYTES + capacity * ENTRY_BYTES + table_slots * 4
        candidate = dict(capacity=capacity, slots=capacity, table_slots=table_slots,
                         slab_bytes=slab, allocated_bytes=slab + ARRAY_HEADER_BYTES,
                         payload_bytes=slab - HEADER_BYTES,
                         ndarray_header_bytes=ARRAY_HEADER_BYTES,
                         format_header_bytes=HEADER_BYTES, policy="global_lru",
                         budget_bytes=budget, max_occupancy_bits_per_slot=(slab + ARRAY_HEADER_BYTES) * 8 / capacity)
        if best is None or capacity > best["capacity"]:
            best = candidate
    return best or dict(capacity=0, slots=0, table_slots=0, slab_bytes=0,
                        allocated_bytes=0, payload_bytes=0, ndarray_header_bytes=0,
                        format_header_bytes=0, policy="global_lru", budget_bytes=budget,
                        max_occupancy_bits_per_slot=0.0)


def allocate(spec):
    slab = np.zeros(spec["slab_bytes"], np.uint8)
    if spec["capacity"]:
        assert sys.getsizeof(slab) == spec["allocated_bytes"] <= spec["budget_bytes"]
        slab[12:16] = np.frombuffer(int(spec["capacity"]).to_bytes(4, "little"), np.uint8)
        slab[16:20] = np.frombuffer(int(spec["table_slots"]).to_bytes(4, "little"), np.uint8)
    return slab


@njit(cache=True, inline="always")
def _key(data, entry):
    return _get(data, (HEADER_BYTES + (entry - 1) * ENTRY_BYTES) * 8, 64)


@njit(cache=True, inline="always")
def _prev(data, entry):
    return np.int64(_get(data, (HEADER_BYTES + (entry - 1) * ENTRY_BYTES + 8) * 8, 32))


@njit(cache=True, inline="always")
def _next(data, entry):
    return np.int64(_get(data, (HEADER_BYTES + (entry - 1) * ENTRY_BYTES + 12) * 8, 32))


@njit(cache=True, inline="always")
def _set_prev(data, entry, value):
    _set(data, (HEADER_BYTES + (entry - 1) * ENTRY_BYTES + 8) * 8, 32, np.uint64(value))


@njit(cache=True, inline="always")
def _set_next(data, entry, value):
    _set(data, (HEADER_BYTES + (entry - 1) * ENTRY_BYTES + 12) * 8, 32, np.uint64(value))


@njit(cache=True, inline="always")
def _table(data, capacity, slot):
    return np.int64(_get(data, (HEADER_BYTES + capacity * ENTRY_BYTES + slot * 4) * 8, 32))


@njit(cache=True, inline="always")
def _set_table(data, capacity, slot, value):
    _set(data, (HEADER_BYTES + capacity * ENTRY_BYTES + slot * 4) * 8, 32, np.uint64(value))


@njit(cache=True)
def _find(data, h, capacity, table_slots):
    mask = table_slots - 1
    slot = np.int64(np.uint64(h) & np.uint64(mask))
    while True:
        entry = _table(data, capacity, slot)
        if entry == 0 or _key(data, entry) == h:
            return slot, entry
        slot = (slot + 1) & mask


@njit(cache=True)
def _mru(data, entry):
    head = np.int64(_get(data, 0, 32))
    if entry == head:
        return
    before, after = _prev(data, entry), _next(data, entry)
    if before:
        _set_next(data, before, after)
    if after:
        _set_prev(data, after, before)
    else:
        _set(data, 32, 32, np.uint64(before))
    _set_prev(data, entry, 0)
    _set_next(data, entry, head)
    if head:
        _set_prev(data, head, entry)
    else:
        _set(data, 32, 32, np.uint64(entry))
    _set(data, 0, 32, np.uint64(entry))


@njit(cache=True)
def cache_lookup(data, h, capacity, table_slots):
    if capacity == 0:
        return False
    _, entry = _find(data, np.uint64(h), capacity, table_slots)
    if entry:
        _mru(data, entry)
        return True
    return False


@njit(cache=True)
def _delete_table(data, h, capacity, table_slots):
    hole, found = _find(data, h, capacity, table_slots)
    if found == 0:
        return
    mask = table_slots - 1
    j = (hole + 1) & mask
    while True:
        entry = _table(data, capacity, j)
        if entry == 0:
            break
        home = np.int64(_key(data, entry) & np.uint64(mask))
        if ((j - home) & mask) >= ((j - hole) & mask):
            _set_table(data, capacity, hole, entry)
            hole = j
        j = (j + 1) & mask
    _set_table(data, capacity, hole, 0)


@njit(cache=True)
def cache_insert(data, h, safe_length, capacity, table_slots):
    if capacity == 0 or safe_length >= 65:
        return 0
    h = np.uint64(h)
    _, present = _find(data, h, capacity, table_slots)
    if present:
        _mru(data, present)
        return 0
    occupied = np.int64(_get(data, 64, 32))
    evicted = occupied == capacity
    if evicted:
        entry = np.int64(_get(data, 32, 32))
        _delete_table(data, _key(data, entry), capacity, table_slots)
        # Detach old tail before reusing its record.
        before = _prev(data, entry)
        if before:
            _set_next(data, before, 0)
        else:
            _set(data, 0, 32, np.uint64(0))
        _set(data, 32, 32, np.uint64(before))
    else:
        entry = occupied + 1
        _set(data, 64, 32, np.uint64(occupied + 1))
    _set(data, (HEADER_BYTES + (entry - 1) * ENTRY_BYTES) * 8, 64, h)
    _set_prev(data, entry, 0)
    _set_next(data, entry, 0)
    slot, _ = _find(data, h, capacity, table_slots)
    _set_table(data, capacity, slot, entry)
    # New or recycled record is detached; attach as MRU explicitly.
    head = np.int64(_get(data, 0, 32))
    _set_next(data, entry, head)
    if head:
        _set_prev(data, head, entry)
    else:
        _set(data, 32, 32, np.uint64(entry))
    _set(data, 0, 32, np.uint64(entry))
    return 2 if evicted else 1


@njit(cache=True)
def invalidate_for_member(data, member_h, capacity, table_slots):
    """Flush this cache if a newly published member shares a cached full hash.

    Flushing is conservative but correct, and avoids retaining a reverse map or
    uncharged free list for rare dynamic updates. Invoke before member publish.
    """
    if capacity == 0:
        return 0
    _, found = _find(data, np.uint64(member_h), capacity, table_slots)
    if found == 0:
        return 0
    occupied = np.int64(_get(data, 64, 32))
    data[:12] = 0
    data[HEADER_BYTES:] = 0
    return occupied


@njit(cache=True)
def _simulate(stream, hashes, safe_lengths, fp_static, slab, tail_start, capacity, table_slots):
    counts = np.zeros(8, np.int64)
    for i in range(stream.size):
        x = int(stream[i])
        if cache_lookup(slab, hashes[x], capacity, table_slots):
            counts[2] += 1
            if i >= tail_start:
                counts[3] += 1
        elif fp_static[x]:
            counts[0] += 1
            if i >= tail_start:
                counts[1] += 1
            outcome = cache_insert(slab, hashes[x], int(safe_lengths[x]), capacity, table_slots)
            if outcome:
                counts[4] += 1
                counts[5] += outcome == 2
                counts[7] += outcome == 1
            else:
                counts[6] += 1
    return counts


def simulate(stream, hashes, safe_lengths, fp_static, cache_bytes, tail_start=0,
             policy="lru", prefix_bits=64):
    spec = layout(cache_bytes)
    slab = allocate(spec)
    counts = _simulate(np.asarray(stream, np.int64), np.asarray(hashes, np.uint64),
                       np.asarray(safe_lengths, np.int16), np.asarray(fp_static, np.bool_),
                       slab, int(tail_start), spec["capacity"], spec["table_slots"])
    names = ("fp_full", "fp_tail", "hits_full", "hits_tail", "inserts", "evictions", "bypasses", "occupied")
    out = {k: int(v) for k, v in zip(names, counts)}
    out.update(spec)
    out["actual_bits_per_occupied"] = spec["allocated_bytes"] * 8 / max(1, out["occupied"])
    return out

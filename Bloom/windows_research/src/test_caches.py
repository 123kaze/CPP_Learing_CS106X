"""Deterministic independent references and safety checks for packed caches."""
from collections import OrderedDict
from pathlib import Path
import json
import sys
import time
import numpy as np
import compact_cache as C
import global_lru as G

ROOT = Path(__file__).resolve().parents[1]


def reference_global(stream, hashes, lengths, fp_static, capacity, tail):
    entries = OrderedDict()
    counts = [0] * 8
    for i, x in enumerate(stream):
        h = int(hashes[x])
        if h in entries:
            entries.move_to_end(h)
            counts[2] += 1
            counts[3] += i >= tail
        elif fp_static[x]:
            counts[0] += 1
            counts[1] += i >= tail
            if not capacity or lengths[x] >= 65:
                counts[6] += 1
                continue
            if len(entries) == capacity:
                entries.popitem(last=False)
                counts[5] += 1
            entries[h] = True
            counts[4] += 1
    counts[7] = len(entries)
    return counts


def reference_quotient(stream, hashes, lengths, fp_static, spec, tail):
    q = spec["qbits"]
    buckets, hands = {}, {}
    counts = [0] * 8
    tick = 0
    for i, x in enumerate(stream):
        h = int(hashes[x])
        b = h >> (64 - q) if q else 0
        bucket = buckets.setdefault(b, [None] * 4)
        hit = -1
        if q:
            for j, rec in enumerate(bucket):
                if rec is not None and (h >> (64 - rec[1])) == rec[0]:
                    hit = j
                    break
        if hit >= 0:
            counts[2] += 1
            counts[3] += i >= tail
            if spec["policy_code"]:
                tick += 1
                bucket[hit][2] = tick
            else:
                bucket[hit][2] = 1
        elif fp_static[x]:
            counts[0] += 1
            counts[1] += i >= tail
            if not q or lengths[x] > spec["prefix_bits"]:
                counts[6] += 1
                continue
            free = next((j for j, rec in enumerate(bucket) if rec is None), -1)
            if free < 0:
                counts[5] += 1
                if spec["policy_code"]:
                    free = min(range(4), key=lambda j: bucket[j][2])
                else:
                    hand = hands.get(b, 0)
                    while bucket[hand][2]:
                        bucket[hand][2] = 0
                        hand = (hand + 1) % 4
                    free = hand
                    hands[b] = (hand + 1) % 4
            length = max(q, int(lengths[x]))
            tick += spec["policy_code"]
            bucket[free] = [h >> (64 - length), length, tick if spec["policy_code"] else 1]
            counts[4] += 1
    counts[7] = sum(rec is not None for bucket in buckets.values() for rec in bucket)
    return counts


def main():
    started = time.time()
    checks = []
    rng = np.random.default_rng(20261028)
    slab = np.zeros(40, np.uint8)
    for width in range(1, 65):
        for offset in range(8):
            value = int(rng.bit_generator.random_raw()) & ((1 << width) - 1)
            before = slab.copy()
            C._set(slab, 8 + offset, width, np.uint64(value))
            assert int(C._get(slab, 8 + offset, width)) == value
            oldbits = np.unpackbits(before, bitorder="little")
            newbits = np.unpackbits(slab, bitorder="little")
            assert np.array_equal(oldbits[:8 + offset], newbits[:8 + offset])
            assert np.array_equal(oldbits[8 + offset + width:], newbits[8 + offset + width:])
    checks.append("512 unaligned bitfield round trips including uint64 maximum width")

    members = np.sort(rng.integers(0, np.iinfo(np.uint64).max, 5000, dtype=np.uint64))
    hashes = rng.integers(0, np.iinfo(np.uint64).max, 4000, dtype=np.uint64)
    lengths = C.safe_prefix_lengths(members, hashes)
    # Independent string-prefix definition, not a reimplementation of the binary search.
    for j in range(30):
        bits = f"{int(hashes[j]):064b}"
        expected = min(l for l in range(65)
                       if not any(f"{int(m):064b}"[:l] == bits[:l] for m in members))
        assert lengths[j] == expected
    assert C.safe_prefix_length(members, members[0]) == 65
    assert C.safe_prefix_length(np.empty(0, np.uint64), np.uint64(0)) == 0
    checks.append("member-verified lengths match independent exhaustive prefix definition; collisions bypass")

    stream = rng.integers(0, len(hashes), 40000, dtype=np.int64)
    fp = rng.random(len(hashes)) < .7
    tail = len(stream) // 4
    names = ("fp_full", "fp_tail", "hits_full", "hits_tail", "inserts", "evictions", "bypasses", "occupied")
    comparisons = []
    for policy in ("clock", "lru"):
        for budget in (0, 255, 1024, 4096):
            spec = C.layout(budget, policy=policy)
            actual = C.simulate(stream, hashes, lengths, fp, budget, tail, policy)
            expected = reference_quotient(stream, hashes, lengths, fp, spec, tail)
            assert [actual[n] for n in names] == expected, (policy, budget, actual, expected)
            if spec["slots"]:
                allocated = C.allocate(spec)
                assert sys.getsizeof(allocated) == spec["allocated_bytes"] <= budget
            comparisons.append({"backend": spec["policy"], "budget": budget,
                                "counts": expected, "layout": spec})
    checks.append("packed CLOCK and timestamp bucket-LRU match independent references over 8 x 40000 queries")

    # Deliberately collide the low hash bits to exercise backward-shift deletion,
    # including zero and maximum uint64 keys (neither is an empty sentinel).
    adversarial_hashes = (np.arange(150, dtype=np.uint64) << np.uint64(24))
    adversarial_hashes[-1] = np.uint64(0xFFFFFFFFFFFFFFFF)
    ls = np.ones(len(adversarial_hashes), np.int16)
    ls[4] = 65
    st = rng.integers(0, len(ls), 20000, dtype=np.int64)
    fps = rng.random(len(ls)) < .8
    for budget in (0, 255, 1024, 4096):
        spec = G.layout(budget)
        actual = G.simulate(st, adversarial_hashes, ls, fps, budget, len(st) // 4)
        expected = reference_global(st, adversarial_hashes, ls, fps, spec["capacity"], len(st) // 4)
        assert [actual[n] for n in names] == expected, (budget, actual, expected)
        if spec["capacity"]:
            assert sys.getsizeof(G.allocate(spec)) == spec["allocated_bytes"] <= budget
        comparisons.append({"backend": "global_lru", "budget": budget,
                            "counts": expected, "layout": spec})
    checks.append("exact global LRU matches OrderedDict over 4 x 20000 queries with hostile table collisions")

    for policy in ("clock", "lru"):
        spec = C.layout(4096, policy=policy)
        data = C.allocate(spec)
        args = [spec[k] for k in ("qbits", "rbits", "slot_bits", "policy_code")]
        for j in range(3000):
            if not C.cache_lookup(data, hashes[j], *args):
                C.cache_insert(data, hashes[j], int(lengths[j]), *args)
        assert not any(C.cache_lookup(data, h, *args) for h in members)
        h = hashes[-1]
        if not C.cache_lookup(data, h, *args):
            C.cache_insert(data, h, int(lengths[-1]), *args)
        assert C.cache_lookup(data, h, *args)
        removed = C.invalidate_for_member(data, h, *args[:3])
        assert removed >= 1 and not C.cache_lookup(data, h, *args)
        before = data.copy()
        assert C.cache_insert(data, h, 65, *args) == 0
        assert np.array_equal(data, before)
    checks.append("zero cached-prefix matches for all 5000 members after saturation, both policies")
    checks.append("new-member prefix invalidation removes the conflict before publication; length65 bypass does not mutate cache")

    spec = G.layout(4096)
    data = G.allocate(spec)
    for h in hashes[:40]:
        G.cache_insert(data, h, 1, spec["capacity"], spec["table_slots"])
    assert G.cache_lookup(data, hashes[0], spec["capacity"], spec["table_slots"])
    assert G.invalidate_for_member(data, hashes[0], spec["capacity"], spec["table_slots"]) == 40
    assert not G.cache_lookup(data, hashes[0], spec["capacity"], spec["table_slots"])
    assert G.cache_insert(data, hashes[1], 1, spec["capacity"], spec["table_slots"]) == 1
    assert G.cache_lookup(data, hashes[1], spec["capacity"], spec["table_slots"])
    checks.append("global-LRU dynamic member collision safely flushes before publication and remains usable")

    result = dict(status="passed", checks=checks, elapsed_seconds=time.time() - started,
                  random_seed=20261028, comparisons=comparisons,
                  caveats=["bucket_lru is per-bucket LRU; global_lru is exact global LRU",
                           "format reserves maximum remainder width; actual per-entry length varies but storage width does not",
                           "correctness is with respect to uint64 member hashes; exact equal hashes bypass",
                           "sorted member index is authoritative backend state, separate from cache allocation"])
    out = ROOT / "evidence" / "cache-tests.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "comparisons"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

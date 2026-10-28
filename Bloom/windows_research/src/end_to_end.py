"""Live LightGBM traversal + packed BF + verified compact-cache benchmark.

The timed region traverses trees for each cache miss (before placement) or each
query (after placement).  It includes membership-index searches on cache inserts
and the complete 5128-byte HLL/Space-Saving updates.  Backend latencies are
explicit projections, not measured I/O.  Input features/trace and the external
authoritative member index are reported separately from filter resident bytes.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
from numba import njit

TREE_KEYS = ("feat", "thr", "left", "right", "leaf", "roots")
SKETCH_BYTES = 5128


def model_arrays(booster, t=None):
    """An executable, compact tree representation; every resident byte counted.

    Numeric finite input features only.  int16 is sufficient for 200 x 31-leaf
    trees; assert rather than silently truncate when passed a larger model.
    """
    feat, thr, left, right, leaf, roots = [], [], [], [], [], []
    trees = booster.dump_model()["tree_info"]
    if t is not None:
        trees = trees[:t]
    for tree in trees:
        def walk(node):
            if "leaf_value" in node:
                leaf.append(node["leaf_value"])
                return ~ (len(leaf) - 1)
            if node["decision_type"] != "<=":
                raise ValueError("Categorical splits require another encoder")
            idx = len(feat)
            feat.append(node["split_feature"])
            thr.append(node["threshold"])
            left.append(0)
            right.append(0)
            left[idx] = walk(node["left_child"])
            right[idx] = walk(node["right_child"])
            return idx
        roots.append(walk(tree["tree_structure"]))
    if max(len(feat), len(leaf), max(feat, default=0)) > 32767:
        raise ValueError("Tree representation exceeds int16 index range")
    return dict(feat=np.asarray(feat, np.int16), thr=np.asarray(thr, np.float64),
                left=np.asarray(left, np.int16), right=np.asarray(right, np.int16),
                leaf=np.asarray(leaf, np.float64), roots=np.asarray(roots, np.int16))


@njit(cache=True)
def model_score(x, feat, thr, left, right, leaf, roots):
    score = 0.0
    for root in roots:
        n = np.int64(root)
        while n >= 0:
            n = np.int64(left[n] if x[feat[n]] <= thr[n] else right[n])
        score += leaf[~n]
    return score


@njit(cache=True)
def predict_raw(X, feat, thr, left, right, leaf, roots):
    out = np.empty(X.shape[0], np.float64)
    for i in range(X.shape[0]):
        out[i] = model_score(X[i], feat, thr, left, right, leaf, roots)
    return out


@njit(cache=True)
def mix64(z):
    z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return z ^ (z >> np.uint64(31))


@njit(cache=True)
def filter_query(score, h, cuts, kind, off, m, k, bf):
    g = np.searchsorted(cuts, score, side="right")
    if kind[g] == 0:
        return True
    if kind[g] != 1:
        return False
    for j in range(k[g]):
        pos = np.int64(mix64(h + np.uint64(j + 1) * np.uint64(0x9E3779B97F4A7C15)) % np.uint64(m[g]))
        bit = off[g] + pos
        if (bf[bit >> 3] & (np.uint8(1) << np.uint8(bit & 7))) == 0:
            return False
    return True


@njit(cache=True)
def hll_add(regs, h):
    idx = np.int64(h >> np.uint64(54))
    w = h << np.uint64(10)
    rank = 1
    mask = np.uint64(1) << np.uint64(63)
    while rank <= 54 and (w & mask) == 0:
        rank += 1
        mask >>= np.uint64(1)
    if rank > regs[idx]:
        regs[idx] = np.uint8(rank)


@njit(cache=True)
def sketch_fp(h, fp_regs, top_keys, top_counts, top_errors, counter):
    hll_add(fp_regs, h)
    key = np.uint32(h & np.uint64(0xFFFFFFFF))
    hit, mn = -1, 0
    for j in range(top_keys.size):
        if top_counts[j] and top_keys[j] == key:
            hit = j
            break
        if top_counts[j] < top_counts[mn]:
            mn = j
    if hit >= 0:
        top_counts[hit] += np.uint32(1)
    else:
        top_keys[mn] = key
        top_errors[mn] = top_counts[mn]
        top_counts[mn] += np.uint32(1)
    counter[0] += np.uint64(1)


def packed_filter(st):
    if getattr(st, "bits_packed", False) or st.bits.size == (int(st.bf_off[-1]) + 7) // 8:
        bf = st.bits
    elif hasattr(st, "packed_bits"):
        bf = st.packed_bits
    else:
        bf = np.packbits(st.bits, bitorder="little")
    return (np.ascontiguousarray(st.cuts), np.ascontiguousarray(st.kind),
            np.ascontiguousarray(st.bf_off), np.ascontiguousarray(st.m),
            np.ascontiguousarray(st.k), np.ascontiguousarray(bf))


def _pipeline_function():
    # Imported lazily to keep model_arrays usable while runtime is initialized.
    from compact_cache import cache_lookup, cache_insert, safe_prefix_length

    @njit(cache=True)
    def run(X, ids, labels, stream, feat, thr, left, right, leaf, roots,
            cuts, kind, off, m, k, bf, sorted_members, slab,
            qbits, rbits, slot_bits, policy_code, enabled, placement,
            neg_regs, fp_regs, top_keys, top_counts, top_errors, counter):
        # accepted, FP, FN, cache hits, insertions, evictions, index searches,
        # model calls, cache probes, total negatives.
        out = np.zeros(10, np.int64)
        for row in stream:
            h = mix64((np.uint64(ids[row]) ^ np.uint64(0xA5A50001)) + np.uint64(0x9E3779B97F4A7C15))
            member = labels[row]
            hit = False
            if not member:
                hll_add(neg_regs, h)
                out[9] += 1
            if enabled and placement == 0:
                out[8] += 1
                hit = cache_lookup(slab, h, qbits, rbits, slot_bits, policy_code)
            if hit:
                out[3] += 1
                if member:
                    out[2] += 1
                else:
                    sketch_fp(h, fp_regs, top_keys, top_counts, top_errors, counter)
                continue
            out[7] += 1
            score = model_score(X[row], feat, thr, left, right, leaf, roots)
            accept = filter_query(score, h, cuts, kind, off, m, k, bf)
            if not accept:
                if member:
                    out[2] += 1
                continue
            if enabled and placement == 1:
                out[8] += 1
                hit = cache_lookup(slab, h, qbits, rbits, slot_bits, policy_code)
            if hit:
                out[3] += 1
                if member:
                    out[2] += 1
                else:
                    sketch_fp(h, fp_regs, top_keys, top_counts, top_errors, counter)
                continue
            out[0] += 1
            if not member:
                out[1] += 1
                sketch_fp(h, fp_regs, top_keys, top_counts, top_errors, counter)
                if enabled:
                    out[6] += 1
                    length = safe_prefix_length(sorted_members, h)
                    status = cache_insert(slab, h, length, qbits, rbits, slot_bits, policy_code)
                    if status:
                        out[4] += 1
                    if status == 2:
                        out[5] += 1
        return out
    return run


def make_mixed_stream(setup, positives, count, workload, seed=20261028):
    """Actual labeled member/nonmember requests; retained order shared by modes."""
    rng = np.random.default_rng(seed)
    neg_rows = np.flatnonzero(setup.split["neg_test"])
    mem_rows = np.flatnonzero(setup.y)
    is_pos = np.zeros(count, np.bool_)
    is_pos[rng.choice(count, int(round(count * positives)), replace=False)] = True
    out = np.empty(count, np.int64)
    out[is_pos] = rng.choice(mem_rows, int(is_pos.sum()), replace=True)
    nneg = int((~is_pos).sum())
    if workload == "uniform":
        out[~is_pos] = rng.choice(neg_rows, nneg, replace=True)
    elif workload == "zipf1.1-10k":
        subset = rng.choice(neg_rows, min(10000, neg_rows.size), replace=False)
        cdf = np.cumsum(np.arange(1, subset.size + 1, dtype=np.float64) ** -1.1)
        rank = np.searchsorted(cdf / cdf[-1], rng.random(nneg))
        out[~is_pos] = subset[rank]
    else:
        raise ValueError(workload)
    return out


def benchmark(setup, booster_path, configs, output_dir, queries=1000000, reps=3,
              workloads=("uniform", "zipf1.1-10k")):
    """Benchmark supplied executable structures. Writes incremental real rows."""
    from compact_cache import layout
    import runtime
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    output = outdir / f"end_to_end_{setup.name}.json"
    booster = lgb.Booster(model_file=str(booster_path))
    X = getattr(setup, "X", None)
    if X is None:
        _, _, X, _ = runtime.C.load_dataset(setup.name)
    X = np.ascontiguousarray(X)
    ids = np.asarray(setup.ids, dtype=np.uint64)
    labels = np.asarray(setup.y)
    sorted_members = getattr(setup, "member_hashes", None)
    if sorted_members is None:
        sorted_members = np.sort(setup.h1m)
    pipeline = _pipeline_function()
    rows = []
    metadata = dict(dataset=setup.name, queries=queries, repeats=reps,
                    python=platform.python_version(), cpu=platform.processor(),
                    platform=platform.platform(),
                    query_input_bytes=int(X.nbytes + ids.nbytes + labels.nbytes),
                    external_member_index_bytes=int(sorted_members.nbytes),
                    backend_latency_measured=False,
                    timing="median of repeats; JIT and 25% warmup excluded; single-thread compiled live traversal",
                    included_costs="key hashing, live tree traversal, packed BF, cache lookup/insertion/replacement, member-index search on insertion, sketch updates",
                    excluded_costs="feature extraction from original objects, input trace generation, compilation, model construction, network/disk/backend I/O",
                    sketch_bytes=SKETCH_BYTES,
                    sketch_semantics="negative HLL on every known negative; FP sketch on backend false positives and cache hits",
                    placement_equivalence="Prefixes can hit additional negatives; recency may make placements diverge. Counts are independently measured.")
    for config in configs:
        st = config["structure"]
        trees = int(config["trees"])
        tree = model_arrays(booster, trees)
        ta = tuple(tree[k] for k in TREE_KEYS)
        sample = np.arange(0, X.shape[0], max(1, X.shape[0] // 5000))
        native = predict_raw(X[sample], *ta)
        reference = booster.predict(X[sample], raw_score=True, num_iteration=trees, num_threads=1)
        max_error = float(np.max(np.abs(native - reference)))
        if not np.allclose(native, reference, atol=1e-10, rtol=1e-10):
            raise AssertionError(f"Tree traversal mismatch {max_error}")
        filt = packed_filter(st)
        cache_bytes = int(config["cache_bytes"])
        L = layout(cache_bytes, policy=config.get("policy", "clock"))
        enabled = cache_bytes > 0 and L["slab_bytes"] > 0
        for workload in workloads:
            for pos in (0.1, 0.5):
                stream = make_mixed_stream(setup, pos, queries, workload)
                tail = queries // 4
                paired = {}
                for placement, label in ((0, "cache_before"), (1, "cache_after")):
                    timings, counts = [], []
                    for rep in range(reps):
                        slab = np.zeros(L["slab_bytes"], np.uint8)
                        neg_regs = np.zeros(1024, np.uint8)
                        fp_regs = np.zeros(1024, np.uint8)
                        top_keys = np.zeros(256, np.uint32)
                        top_counts = np.zeros(256, np.uint32)
                        top_errors = np.zeros(256, np.uint32)
                        counter = np.zeros(1, np.uint64)
                        sketch_nbytes = sum(a.nbytes for a in (neg_regs, fp_regs, top_keys, top_counts, top_errors, counter))
                        assert sketch_nbytes == SKETCH_BYTES
                        args = (X, ids, labels, *ta, *filt, sorted_members, slab,
                                L["qbits"], L["rbits"], L["slot_bits"], L["policy_code"],
                                enabled, placement, neg_regs, fp_regs,
                                top_keys, top_counts, top_errors, counter)
                        # Explicit ordering lets warmup state survive into tail.
                        def invoke(s):
                            return pipeline(args[0], args[1], args[2], s, *args[3:])
                        warm = invoke(stream[:tail])
                        started = time.perf_counter_ns()
                        result = invoke(stream[tail:])
                        elapsed = time.perf_counter_ns() - started
                        assert warm[2] == 0 and result[2] == 0, "False negative in live pipeline"
                        timings.append(elapsed / (queries - tail))
                        counts.append(result)
                    assert all(np.array_equal(counts[0], c) for c in counts[1:]), "Nondeterministic counts"
                    c = counts[0]
                    measured_ns = float(np.median(timings))
                    n = queries - tail
                    row = dict(dataset=setup.name, budget_kib=config["budget_kib"], trees=trees,
                               cache_bytes=cache_bytes, cache_allocated_bytes=L["allocated_bytes"],
                               workload=workload, positive_fraction=pos, placement=label,
                               evaluated_queries=n, mean_query_ns=measured_ns,
                               repeat_mean_query_ns=timings,
                               measured_throughput_qps=1e9 / measured_ns,
                               accepted=int(c[0]), false_positives=int(c[1]), false_negatives=int(c[2]),
                               cache_hits=int(c[3]), insertions=int(c[4]), evictions=int(c[5]),
                               member_index_searches=int(c[6]), model_calls=int(c[7]), cache_probes=int(c[8]),
                               negative_queries=int(c[9]), fpr=int(c[1]) / max(1, int(c[9])),
                               raw_score_max_error=max_error,
                               model_array_bytes=sum(a.nbytes for a in tree.values()),
                               packed_bf_bytes=int(filt[-1].nbytes), sketch_bytes=SKETCH_BYTES,
                               navigation_bytes=int(getattr(st, "metadata_bytes", 0)),
                               array_overhead_bytes=int(getattr(st, "array_overhead_bytes", 0)),
                               actual_filter_state_bytes=int(getattr(st, "used_bytes", 0))-cache_bytes+L["allocated_bytes"],
                               resident_accounting="Executable packed model/BF/navigation/sketch arrays, their ndarray headers, model dictionary, and cache allocation including its header. Host interpreter/JIT/input/member index reported separately; not process RSS.")
                    row["backend_projections"] = [dict(backend_us=us,
                        projected_mean_query_ns=measured_ns + int(c[0]) / n * us * 1000,
                        projected_throughput_qps=1e9 / (measured_ns + int(c[0]) / n * us * 1000))
                        for us in (1, 10, 100)]
                    rows.append(row)
                    paired[label] = row
                    output.write_text(json.dumps(dict(metadata=metadata, rows=rows), ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"e2e {setup.name} {config['budget_kib']}KiB t{trees} {workload} positive={pos} {label}: {measured_ns:.1f}ns, FP={c[1]}, FN={c[2]}", flush=True)
                for row in paired.values():
                    row["paired_false_positive_difference"] = paired["cache_before"]["false_positives"] - paired["cache_after"]["false_positives"]
    output.write_text(json.dumps(dict(metadata=metadata, rows=rows), ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--budgets", required=True)
    parser.add_argument("--queries", type=int, default=1000000)
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--cache-frac", type=float, default=0.1)
    parser.add_argument("--trees", type=int, default=48)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "results")
    args = parser.parse_args()
    import runtime
    setup = runtime.load_setup(args.dataset)
    scores = runtime.scores_for(setup, args.dataset)
    configs = []
    for kib in map(int, args.budgets.split(",")):
        cache = int(kib * 1024 * args.cache_frac)
        st = runtime.structure(setup, scores, args.trees, kib * 1024, cache, SKETCH_BYTES)
        configs.append(dict(structure=st, trees=args.trees, budget_kib=kib, cache_bytes=cache))
    benchmark(setup, runtime.C.CACHE / args.dataset / "model200.txt", configs,
              args.output_dir, args.queries, args.reps)


if __name__ == "__main__":
    main()

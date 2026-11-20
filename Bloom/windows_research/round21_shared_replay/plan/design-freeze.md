# Round21: safe shared replay, unchanged round20 decisions

## Scope

Only optimize replay execution. Keep the round20 rule:13 physically accounted BF/cache candidates plus the repaired RA6 winner; lower actual learning FP wins, ties choose the same BF winner. No KL gate, unseen-mass shrinkage, new shortlist, candidate truncation or heuristic pruning. Those proposals are undergoing independent theoretical review in a separate directory and cannot change this measured code.

The previous message had described full-run next steps before launching them. At this freeze only eight unit tests and two actual CAIDA TCP16KiB pilots had run; no formal performance measurement has been reported or selected.

## Safe sparse routing

A static-negative query can match a stored verified prefix and alter CLOCK reference bits. Routing solely by static BF flags is incorrect: the retained one-bucket counterexample gives6 FP for the full sequence and7 if such a request is removed.

For each cached candidate, route every observed static-positive key and every observed key that could match ANY insertible observed positive key's stored prefix. Intersect each potential prefix's64-bit interval with the actual quotient bucket range, union these intervals and sweep sorted observed hashes. For fp64, include all equal64-bit fingerprint aliases, including static-negative keys. Unsafe lengths>40 are not insertion intervals but their static-positive requests are still routed. Do not assume absent fingerprint collisions or ignore cross-key hits.

Store separate packed candidate acceptance and route masks (one uint64 per64 candidates per observed key). The joint loop traverses the original learning sequence once, maps the key to its observed-key index and dispatches only set route bits; each candidate owns its original packed CLOCK array. This is one ORDERED SIMULATION traversal, not one total input read: counting/model preparation and route construction also cost work.

No-cache candidates use exact weighted counts; cached candidates in the shared loop finish the full sequence without early stopping. The old serial comparator retains incumbent early stopping/no-cache shortcuts. Doing more candidate work can make joint replay slower; do not remove early stopping from the comparison to manufacture a speedup.

Routing cost includes sorting, interval construction, local-map creation, bitmasks and cache allocation. Disclose route workspace and candidate event visits, including cross-prefix non-FP events. Do not claim O(L+static-FP events) for indexed cache; the dispatch term includes potential state-changing non-FP events and preprocessing need not be O(D).

## Verification matrix and timing points

All192 round20 cases, both cache formats, same prepared models/data/streams. Freshly construct the repaired RA6 anchor and13 BF candidates. For every case:
- Complete original per-candidate replay (no cutoff) and shared replay must match all eight counters and EVERY packed cache byte for each of14 candidates (2688 pairs).
- Original early-stopping gate and shared exact counts must select the same candidate and match round20's learning costs, selected configuration, full-pool static flags and actual tail FP.
- No test-tail information affects route building or selection.

Two pre-freeze CAIDA TCP16KiB pilots (one per format) passed and are excluded. Synthetic tests cover cross-prefix eviction, full-fingerprint aliasing, random candidates,180 candidates spanning three mask words, bucket clipping, uint64 end points, unsafe lengths and no-cache shortcuts. An initial test found differing no-cache bypass-counter conventions between index/fp64; corrected BEFORE formal freeze, without changing outputs or cache behavior.

Paired replay timings at16 prespecified settings: each of the four TCP datasets at its second budget; COD1024/URL128/CAIDA256/Shalla1024 on Zipf1.0-full seed0; both cache formats. Three in-process repetitions with alternating serial/shared order, after small unrelated kernel warmup. Include all route preprocessing in the shared timer. Common summary/anchor/all-BF construction is measured once per case and stored separately. These are replay microbenchmarks, not three independent full-construction retrainings. Any sum of common prep plus replay is explicitly an accounted composite, not a fresh train-to-ready measurement.

Fair optimized full-grid controls: URL128 and CAIDA256, Zipf1.0-full seed0, both formats; ALL learned candidates plus13 zero candidates get the SAME shared routing/loop optimization. Verify every candidate counter and final cache against full original replay, match the original early-stopping full-grid winner and archived configuration, then measure three alternating serial/shared repetitions. This avoids attributing a generally applicable replay optimization solely to RA6. Full-grid count/build costs remain separately recorded; methods search different candidate families and should not be represented as the same optimizer.

## Operations and claims

All jobs serial, single-threaded. Frozen source/input hashes checked. No failed/partial-result automatic retry; memory pressure restart requires approval. Preserve raw timings including regressions. Peak process RSS includes setup and verification and is not deployment memory. No old experiment/paper edits and no restored deleted publication content. Do not claim the original2–5× or49.24× speedups survive without new measurements.

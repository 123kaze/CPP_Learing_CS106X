# Round 16: real RocksDB lookup + backend-confirmed feedback (2026-11-18)

## Purpose and prior limitations

Test whether lower filter FP counts translate into lower actual key-value query latency when RocksDB already has internal Bloom filters and a block cache. No injected sleeps, artificial per-access latency or projected network gains.

Round6 E8 used real SQLite reads, but classified a whole batch and inserted cache entries from known labels before backend reads. This round is a synchronous, single-client integration: external probe -> real Get if accepted -> negative-cache feedback ONLY if Get returns None. No true-membership array or precomputed FP flags enter the decision path. A static read-only snapshot prevents stale negative entries after inserts; updates/deletes/concurrency are not evaluated.

## Fixed data and configurations

- Frozen URL dataset:213,045 member keys, original hash-based training/validation/negative-pool split and18 precomputed URL features. Database keys are the original uint64 IDs encoded as8-byte big-endian bytes, not feature vectors. This is real dataset-derived membership, NOT a production DB trace.
- Values are4096 bytes: matching8-byte key header plus deterministic incompressible random payload(seed16003). SST snapshot841.5MiB (record exact bytes and digest), flushed and compacted before measurements. Values are retrieved and checked, not merely key_may_exist.
- rocksdict0.3.29 Python3.12 macOS-arm64 binary, isolated under .deps/py312. Default RocksDB compression/compaction retained; full internal Bloom enabled at10 bits/key, block size4096. Table index/filter blocks participate in the same block cache. Row cache not artificially added or native filters disabled.
- Block-cache regimes:1GiB (intended to fit the841.5MiB snapshot),8MiB (block-cache pressure). Every fresh query process first reads every member once in the identical order, then measures with a COLD EXTERNAL cache. Record actual data-block hit/miss counters; intended fit/pressure labels are not proof of achieved residency.
- OS page cache is NOT evicted and direct I/O is NOT forced. Block-cache misses/bytes returned are not physical device I/O. Report RocksDB counter deltas and process page faults without calling them disk reads.
- External filter budget128KiB for all filtered methods: Direct (no external filter), ordinary BF+learning-Replay-selected cache, shared Gama(no cache), frozen RA6, same learned candidate space Replay. The existing verified-prefix CLOCK format is used; no probabilistic fp64 shortcut.
- Same frozen tree prefixes/cache fractions/DP/probe hash/CLOCK selection rules; fresh200-tree model uses seed1,31 leaves,learning_rate0.1, one thread. Chunked pred_leaf is reused only for construction. Native query path traverses selected trees and BF bits anew, with live scalar key hashing.
- The deployment representation stores only DP-region thresholds, not a1000-segment navigation table. Full-member and negative-pool acceptance must exactly match frozen E5.build; physical owning-array bytes+cache <=128KiB. Runtime/interpreter/JIT overhead and request features are not counted as filter bytes. The member safety index(8B/member) remains separate and is reported; nominal filter budgets are not equal whole-process memory budgets.

## Workloads and training protocol

Two fixed negative streams (seed16001), each50K learning+150K evaluation negatives:
1. Zipf1.0 over the full negative pool with fixed random rank-to-key permutation.
2. Once: random permutation without replacement, learning/evaluation disjoint; low-repeat control.

Mix16,667 member queries uniformly into each evaluation stream(seed16002) and shuffle, resulting166,667 queries with about10% true hits. The exact same streams are used by all methods/cache regimes/repetitions. Learning negatives are explicitly checked via real database Gets before selection; no evaluation labels used for tuning. Selection optimizes negative queries with H=150K. The member set for constructing a membership filter is construction input, not a per-request oracle.

Three fresh construction processes train/build the model and select every method for both workloads. All-method common learned work is measured once in each repetition and charged to each learned method's standalone readiness; BF is not charged any model cost. Cache safety preprocessing and actual learning DB acquisition are separately measured and charged where required. These preparation costs are not CPU-overlapped with query timing. Database creation, input materialization, JIT and serialization are outside filter readiness and individually reported/excluded. Source/model/config/flags/artifact digests are retained.

## Timings and correctness

Formal query matrix:5 methods ×2 workloads ×2 block-cache sizes ×3 fresh processes =60 queries runs. Serial, application threads=1, rotate method order by repetition plus setting. NoFilter remains a genuine direct Python RocksDB Get loop, not padded with external-filter work. Python/Numba boundary costs are included for filtered methods and disclosed; results concern this integration, not an optimally fused C++ implementation.

Per-query latency includes live probe, real Get, return handling and optional confirmed-miss update, and excludes only the outer-loop inter-query bookkeeping. Overall elapsed/throughput includes the loop and recording overhead; report both mean request latency and elapsed/query. p50/p95/p99 are actual individual-query percentiles, NOT batch averages. Full compressed latency arrays and raw RocksDB counters retained.

Check after timing: every answer equals the immutable snapshot truth, value header/length match, all members accepted with populated cache, database key-read counter equals actual Get count, FP backend calls agree with independent correctness-only frozen-kernel simulation. Labels are consulted only after the timed interval. Input features and encoded key bytes are precomputed as shared request inputs; feature extraction from raw URL strings is not measured.

Report throughput, total/query/p95/p99 latency, CPU, Get calls, database-confirmed negative misses, cache hits/insertions, data/index/filter block hits/misses, Bloom useful count, bytes returned/read counters with exact names, peak whole-process RSS and page-fault deltas. Do not call bytes.read storage-device bytes.

Per-repeat preparation+measured-tail cost is reported separately from query-only speedup. An estimated break-even query count is defined only if measured mean per-query saving is positive, using that repetition's readiness difference divided by the measured average saving; it assumes stationary cost and is not a measured crossover trace. When no saving exists, report no estimated payback, not infinity disguised as a successful speedup.

## Pilot, preservation and failure policy

Before freezing, five2048-query zipf/8MiB smoke runs validated backend results and feedback order; they already show that fewer calls need not be faster. Four integration unit checks validate hash equivalence, no insertion on probe alone, insertion after actual None, and unchanged member acceptance. Smoke timings are excluded, parameters not tuned to improve outcomes.

After freezing, run three independent fresh construction repetitions, then60 fresh query processes. Resume only complete matching results; failures/partial artifacts stop without automatic retry. Memory-pressure kills require user permission before restart. Keep all unfavorable results, including ordinary BF+cache or Direct wins. No frozen code/paper edits, no TeX, no claimed production-trace realism or new significant general advantage.


## v2: effective configuration correction (before new formal runs)

The first60 query runs were answer-correct but INVALID for the requested DB configurations: reopening without explicit default-column-family options ignored the supplied Cache/Bloom settings. A read-only diagnosis confirmed requested Cache usage0 and Bloom useful0; supplying column_families={'default':opts} produced matching actual cache usage and1983/2000 useful Bloom negatives. These are not negative/positive performance outcomes to cherry-pick; the treatment was not applied. All old records and frozen code remain in ../round16_rocksdb and are clearly labeled invalid.

This version explicitly supplies the same options to the default column family at each database opening. It references the identical immutable SST snapshot and fixed request files. It reruns all3 construction processes and60 query processes; no old timing is used as formal v2 data.

Before every measured tail: full-member warmup,2000 evenly spaced member probes, then2000 fixed missing-key probes. Verify the actual cache capacity property equals the requested capacity, supplied Cache usage equals the database's cache usage and is nonzero, member-probe data-block hit rate >=95% for1GiB or <=20% for8MiB, and useful internal Bloom >=1900/2000 missing probes. These assertions test the intended treatment, not desired RA6 speedup. All such probes are outside timing, identical across methods; the external filter stays empty. Failure stops before a false result can be reported.

No other filter/query/selection workload changes. The model, input, value size, database snapshot, internal Bloom setting and nominal cache capacities remain the original planned values.

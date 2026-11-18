# INVALID FOR THE TARGET DATABASE CONFIGURATION

The initial60-run campaign completed and returned correct answers, but a post-run audit found that the supplied cache/Bloom options were not applied to the default column family when reopening the database. The supplied Cache object's usage was0, both capacity regimes had identical cache counters, and Bloom useful count was0. These timings must NOT be cited as a comparison with enabled native Bloom or1GiB versus8MiB caches. Preserved as a failed-configuration archive; corrected runs are in ../round16_rocksdb_v2.

# Real RocksDB point-query integration

60 fresh query processes; 3 fresh training/selection repetitions. URL-derived membership and precomputed features, synthetic Zipf/unique lookup sequences, 10% true hits. This is not a production database trace.

The 841.5MiB read-only SST snapshot retains RocksDB's internal 10bits/key Bloom and default compression. Every run warms all members before starting a cold external cache. OS page cache is not cleared. Values are really returned; only a Get returning None permits negative-cache feedback.

Times and percentiles below are medians of three independent timing runs. Speedup is the median of paired Direct/method elapsed ratios; it may differ from the ratio of table medians.

## zipf: fit (1024MiB RocksDB block cache)

| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 2.559 | 65132 | 15.353 | 84.084 | 96.000 | 166,667 | 150,000 | 1.000× |
| BFCache | 0.555 | 300061 | 3.333 | 5.083 | 83.500 | 22,886 | 6,219 | 4.358× |
| Gama | 0.520 | 320496 | 3.120 | 5.333 | 82.666 | 16,820 | 153 | 4.921× |
| RA6 | 0.554 | 300881 | 3.324 | 5.584 | 83.125 | 16,698 | 31 | 4.640× |
| Replay | 0.707 | 235688 | 4.243 | 6.625 | 84.458 | 16,699 | 32 | 3.605× |

| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 71,640 | 129,032 | 35.70% | 0 | 0.000 | 2.559 | 1.000 |
| BFCache | 253 | 24,304 | 1.03% | 0 | 0.802 | 1.357 | 0.564 |
| Gama | 179 | 16,649 | 1.06% | 0 | 6.853 | 7.369 | 2.890 |
| RA6 | 100 | 16,606 | 0.60% | 0 | 9.273 | 9.826 | 3.871 |
| Replay | 100 | 16,604 | 0.60% | 0 | 10.144 | 10.845 | 4.242 |

## zipf: pressure (8MiB RocksDB block cache)

| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 2.435 | 68438 | 14.612 | 83.500 | 89.014 | 166,667 | 150,000 | 1.000× |
| BFCache | 0.610 | 273138 | 3.661 | 6.291 | 85.806 | 22,886 | 6,219 | 4.016× |
| Gama | 0.533 | 312512 | 3.200 | 5.500 | 84.125 | 16,820 | 153 | 4.595× |
| RA6 | 0.542 | 307535 | 3.252 | 5.625 | 84.667 | 16,698 | 31 | 4.508× |
| Replay | 0.675 | 246967 | 4.049 | 6.166 | 84.167 | 16,699 | 32 | 3.480× |

| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 71,640 | 129,032 | 35.70% | 0 | 0.000 | 2.435 | 1.000 |
| BFCache | 253 | 24,304 | 1.03% | 0 | 0.802 | 1.401 | 0.572 |
| Gama | 179 | 16,649 | 1.06% | 0 | 6.853 | 7.332 | 3.011 |
| RA6 | 100 | 16,606 | 0.60% | 0 | 9.273 | 9.767 | 4.030 |
| Replay | 100 | 16,604 | 0.60% | 0 | 10.144 | 10.819 | 4.439 |

## once: fit (1024MiB RocksDB block cache)

| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 2.856 | 58360 | 17.135 | 83.584 | 97.458 | 166,667 | 150,000 | 1.000× |
| BFCache | 0.664 | 250825 | 3.987 | 5.583 | 82.875 | 30,806 | 14,139 | 4.205× |
| Gama | 0.552 | 302168 | 3.309 | 5.459 | 83.000 | 16,767 | 100 | 5.338× |
| RA6 | 0.535 | 311769 | 3.208 | 5.416 | 83.000 | 16,767 | 100 | 5.342× |
| Replay | 0.625 | 266802 | 3.748 | 5.417 | 82.792 | 16,751 | 84 | 4.471× |

| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 2,456 | 203,729 | 1.19% | 0 | 0.000 | 2.856 | 1.000 |
| BFCache | 248 | 34,263 | 0.72% | 0 | 0.934 | 1.614 | 0.565 |
| Gama | 100 | 16,697 | 0.60% | 0 | 6.855 | 7.403 | 2.592 |
| RA6 | 100 | 16,697 | 0.60% | 0 | 9.419 | 9.987 | 3.502 |
| Replay | 100 | 16,675 | 0.60% | 0 | 10.287 | 10.926 | 3.826 |

## once: pressure (8MiB RocksDB block cache)

| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 2.764 | 60297 | 16.585 | 83.584 | 92.125 | 166,667 | 150,000 | 1.000× |
| BFCache | 0.684 | 243511 | 4.107 | 6.000 | 84.375 | 30,806 | 14,139 | 4.039× |
| Gama | 0.501 | 332621 | 3.006 | 4.750 | 82.208 | 16,767 | 100 | 5.537× |
| RA6 | 0.500 | 333560 | 2.998 | 4.792 | 82.209 | 16,767 | 100 | 5.527× |
| Replay | 0.653 | 255145 | 3.919 | 6.000 | 83.167 | 16,751 | 84 | 4.231× |

| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 2,456 | 203,729 | 1.19% | 0 | 0.000 | 2.764 | 1.000 |
| BFCache | 248 | 34,263 | 0.72% | 0 | 0.934 | 1.688 | 0.599 |
| Gama | 100 | 16,697 | 0.60% | 0 | 6.855 | 7.356 | 2.643 |
| RA6 | 100 | 16,697 | 0.60% | 0 | 9.419 | 9.962 | 3.607 |
| Replay | 100 | 16,675 | 0.60% | 0 | 10.287 | 10.932 | 3.944 |

## Interpretation

- RA6 query-only speedup versus direct RocksDB has a favorable median in **4/4 settings**. This count is descriptive, not a significance claim. All losses and slow repeats remain in the archive.
- Fewer database-confirmed negative misses do not imply lower latency. RocksDB already screens misses through its own Bloom filters, while external model traversal, safety feedback and Python/Numba calls add work. This integration does not establish the speed of a fused C++ filter inside RocksDB.
- Cache capacity regimes are validated by the reported data-block hit rates, not by their names alone. Data-block misses can be served from the OS page cache. rocksdb.bytes.read counts returned value bytes, not device reads; all original ticker names and snapshots are retained.
- Mean µs/query uses overall wall time divided by request count. Individual p95/p99 include probe/Get/response/update and exclude outer-loop inter-request bookkeeping; they are not batch averages. Full compressed per-query latency arrays are archived and can be checked with --latencies.
- External filters use <=128KiB of owning filter/cache arrays. Verified-prefix cache users additionally require an external member index (8B/member); request features, interpreter/JIT and database block cache are separate. Total process memory is not matched by nominal filter budgets.
- Construction costs include fresh training/scoring for learned methods, method-specific selection/build, and actual acquisition of the 50K learning negatives from RocksDB where required. BF is not charged model cost; Gama is not charged learning feedback. Common learned preparation is charged to each method as if deployed independently. DB creation and JIT are outside readiness.
- timing_summary.json records estimated break-even query counts per repetition only when measured mean query-time saving is positive. Otherwise the value is null: no estimated payback. These estimates assume stationary average cost; they are not observed crossover traces.
- Each readiness+tail total is calculated per repetition before aggregation. This combines measured filter preparation and a measured query campaign, not an uninterrupted database lifetime; the common DB snapshot creation is excluded for all methods.
- The once control has disjoint learning/evaluation negative keys. The workload mixes true member requests into the evaluation only; selectors see the same negative learning sequence. Post-timing labels and correctness-only oracle simulations are never used for live cache admission.
- Database returned members/values, post-run all-member acceptance, raw key hashes, native filter flags and actual key-read ticker counts were checked. The dataset is an immutable snapshot: invalidation after writes and concurrent clients are not evaluated.
- Five short smoke runs and four integration unit checks preceded the formal source freeze. Their timings are excluded, and no parameter was tuned in response to a preferred performance outcome.

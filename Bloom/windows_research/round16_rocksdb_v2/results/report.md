# Real RocksDB point-query integration

60 fresh query processes; 3 fresh training/selection repetitions. URL-derived membership and precomputed features, synthetic Zipf/unique lookup sequences, 10% true hits. This is not a production database trace.

The 841.5MiB read-only SST snapshot retains RocksDB's internal 10bits/key Bloom and default compression. Every run warms all members, then checks 2000 member reads and 2000 missing-key reads to verify effective block-cache/Bloom configuration before starting a cold external cache. OS page cache is not cleared. Values are really returned; only a Get returning None permits negative-cache feedback.

Times and percentiles below are medians of three independent timing runs. Speedup is the median of paired Direct/method elapsed ratios; it may differ from the ratio of table medians.

## zipf: fit (1024MiB RocksDB block cache)

| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 0.141 | 1183924 | 0.845 | 2.750 | 4.250 | 166,667 | 150,000 | 1.000× |
| BFCache | 0.235 | 710544 | 1.407 | 4.042 | 5.125 | 22,886 | 6,219 | 0.568× |
| Gama | 0.291 | 572264 | 1.747 | 4.458 | 6.333 | 16,820 | 153 | 0.477× |
| RA6 | 0.295 | 564546 | 1.771 | 4.042 | 6.208 | 16,698 | 31 | 0.477× |
| Replay | 0.423 | 394293 | 2.536 | 5.029 | 6.625 | 16,699 | 32 | 0.312× |

| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 17,702 | 0 | 100.00% | 149,147 | 0.000 | 0.141 | 1.000 |
| BFCache | 16,733 | 0 | 100.00% | 6,163 | 0.143 | 0.375 | 2.771 |
| Gama | 16,667 | 0 | 100.00% | 153 | 6.500 | 6.803 | 48.468 |
| RA6 | 16,667 | 0 | 100.00% | 31 | 8.205 | 8.501 | 60.385 |
| Replay | 16,667 | 0 | 100.00% | 32 | 9.103 | 9.553 | 67.862 |

## zipf: pressure (8MiB RocksDB block cache)

| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 0.376 | 443836 | 2.253 | 4.000 | 81.458 | 166,667 | 150,000 | 1.000× |
| BFCache | 0.456 | 365256 | 2.738 | 4.417 | 81.958 | 22,886 | 6,219 | 0.818× |
| Gama | 0.487 | 342090 | 2.923 | 4.958 | 82.459 | 16,820 | 153 | 0.747× |
| RA6 | 0.518 | 321635 | 3.109 | 5.458 | 82.709 | 16,698 | 31 | 0.678× |
| Replay | 0.637 | 261501 | 3.824 | 5.833 | 82.916 | 16,699 | 32 | 0.556× |

| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 490 | 17,212 | 2.77% | 149,147 | 0.000 | 0.376 | 1.000 |
| BFCache | 99 | 16,634 | 0.59% | 6,163 | 0.143 | 0.599 | 1.606 |
| Gama | 98 | 16,569 | 0.59% | 153 | 6.500 | 6.988 | 18.356 |
| RA6 | 98 | 16,569 | 0.59% | 31 | 8.205 | 8.759 | 23.982 |
| Replay | 98 | 16,569 | 0.59% | 32 | 9.103 | 9.787 | 25.622 |

## once: fit (1024MiB RocksDB block cache)

| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 0.154 | 1082517 | 0.924 | 3.000 | 4.083 | 166,667 | 150,000 | 1.000× |
| BFCache | 0.236 | 705631 | 1.417 | 3.959 | 5.250 | 30,806 | 14,139 | 0.652× |
| Gama | 0.301 | 553518 | 1.807 | 4.500 | 6.250 | 16,767 | 100 | 0.511× |
| RA6 | 0.285 | 584680 | 1.710 | 3.834 | 5.292 | 16,767 | 100 | 0.551× |
| Replay | 0.418 | 399103 | 2.506 | 5.000 | 7.375 | 16,751 | 84 | 0.409× |

| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 18,501 | 0 | 100.00% | 148,547 | 0.000 | 0.154 | 1.000 |
| BFCache | 16,852 | 0 | 100.00% | 13,990 | 0.151 | 0.386 | 2.474 |
| Gama | 16,667 | 0 | 100.00% | 100 | 6.513 | 6.814 | 43.460 |
| RA6 | 16,667 | 0 | 100.00% | 100 | 8.292 | 8.578 | 56.180 |
| Replay | 16,667 | 0 | 100.00% | 84 | 9.251 | 9.629 | 62.539 |

## once: pressure (8MiB RocksDB block cache)

| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 0.377 | 442252 | 2.261 | 3.541 | 81.000 | 166,667 | 150,000 | 1.000× |
| BFCache | 0.454 | 366974 | 2.725 | 4.500 | 81.875 | 30,806 | 14,139 | 0.822× |
| Gama | 0.509 | 327424 | 3.054 | 4.958 | 82.209 | 16,767 | 100 | 0.750× |
| RA6 | 0.518 | 321583 | 3.110 | 5.000 | 82.292 | 16,767 | 100 | 0.720× |
| Replay | 0.631 | 264266 | 3.784 | 5.750 | 82.334 | 16,751 | 84 | 0.629× |

| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 109 | 18,392 | 0.59% | 148,547 | 0.000 | 0.377 | 1.000 |
| BFCache | 97 | 16,755 | 0.58% | 13,990 | 0.151 | 0.608 | 1.617 |
| Gama | 98 | 16,569 | 0.59% | 100 | 6.513 | 7.114 | 18.290 |
| RA6 | 98 | 16,569 | 0.59% | 100 | 8.292 | 8.785 | 23.450 |
| Replay | 98 | 16,569 | 0.59% | 84 | 9.251 | 9.851 | 26.028 |

## RA6 relative to ordinary BF+cache

| Workload | Cache regime | Paired RA6 / BF+cache query-time ratio |
|---|---|---:|
| zipf | fit | 1.389 |
| zipf | pressure | 1.206 |
| once | fit | 1.195 |
| once | pressure | 1.137 |

## Interpretation

- RA6 query-only speedup versus direct RocksDB has a favorable median in **0/4 settings**. This count is descriptive, not a significance claim. All losses and slow repeats remain in the archive.
- Fewer database-confirmed negative misses do not imply lower latency. RocksDB already screens misses through its own Bloom filters, while external model traversal, safety feedback and Python/Numba calls add work. This integration does not establish the speed of a fused C++ filter inside RocksDB.
- Cache capacity regimes are validated by the reported data-block hit rates, not by their names alone. Data-block misses can be served from the OS page cache. rocksdb.bytes.read counts returned value bytes, not device reads; all original ticker names and snapshots are retained.
- Mean µs/query uses overall wall time divided by request count. Individual p95/p99 include probe/Get/response/update and exclude outer-loop inter-request bookkeeping; they are not batch averages. Full compressed per-query latency arrays are archived and can be checked with --latencies.
- External filters use <=128KiB of owning filter/cache arrays. Verified-prefix cache users additionally require an external member index (8B/member); request features, interpreter/JIT and database block cache are separate. Total process memory is not matched by nominal filter budgets.
- Construction costs include fresh training/scoring for learned methods, method-specific selection/build, and actual acquisition of the 50K learning negatives from RocksDB where required. BF is not charged model cost; Gama is not charged learning feedback. Common learned preparation is charged to each method as if deployed independently. DB creation and JIT are outside readiness.
- timing_summary.json records estimated break-even query counts per repetition only when measured mean query-time saving is positive. Otherwise the value is null: no estimated payback. These estimates assume stationary average cost; they are not observed crossover traces.
- Each readiness+tail total is calculated per repetition before aggregation. This combines measured filter preparation and a measured query campaign, not an uninterrupted database lifetime; the common DB snapshot creation is excluded for all methods.
- The once control has disjoint learning/evaluation negative keys. The workload mixes true member requests into the evaluation only; selectors see the same negative learning sequence. Post-timing labels and correctness-only oracle simulations are never used for live cache admission.
- Database returned members/values, post-run all-member acceptance, raw key hashes, native filter flags and actual key-read ticker counts were checked. The dataset is an immutable snapshot: invalidation after writes and concurrent clients are not evaluated.
- The original round16 campaign is invalid for the intended native-Bloom/cache-capacity protocol: top-level options did not configure the reopened default column family. Its 60 records are retained but excluded. This v2 explicitly passes default-column-family options and aborts unless effective capacity, residency and Bloom activity are verified; no workload, filter or budget was tuned to improve outcomes.

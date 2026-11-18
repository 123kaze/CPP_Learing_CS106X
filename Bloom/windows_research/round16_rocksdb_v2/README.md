# Round16 v2: real RocksDB lookup with verified configuration

**Complete: 60/60 query processes and 3/3 fresh training/selection processes. The database result is negative for RA6.**

[Full English report](results/report.md) · [中文结论](results/结论.md) · [Individual timing rows](results/timing_rows.csv)

| Workload | Block cache | Paired RA6/Direct time | Paired RA6/BF+cache time |
|---|---|---:|---:|
| Zipf | 1GiB | 2.097 | 1.389 |
| Zipf | 8MiB | 1.475 | 1.206 |
| Unique negatives | 1GiB | 1.816 | 1.195 |
| Unique negatives | 8MiB | 1.388 | 1.137 |

Ratios above 1 favor the baseline. All 12 RA6 repetitions are slower than Direct and BF+cache. Fewer backend-confirmed false positives do not yield faster queries here: native RocksDB Bloom already prevents most negative data-block reads. There is no estimated RA6 payback point versus Direct at the measured average query costs.

## Actual online path

- Immutable URL-derived membership snapshot: 213,045 keys, 4KiB values, 841.5MiB SST. Workload sequences are synthetic Zipf/unique negatives plus 10% members, not a production trace.
- A request runs live scalar hashing and the selected tree/BF/cache. Only an accepted request calls real synchronous `Get`. Only `Get` returning `None` permits negative-cache feedback. No label/static-FP lookup is used in this decision path.
- Native RocksDB 9.8.4 Bloom(10bits/key), default compression and caches remain active. Every reopened default column family explicitly receives the options.
- Before each timed run, actual cache capacity/usage, member-probe residency and useful Bloom counters are asserted. Full-member warmup is followed by the same 2000 member / 2000 missing-key probes. The external cache starts empty.
- OS page cache is not evicted. A RocksDB data-block miss is not claimed to be a device read. Python/Numba boundary cost is included; fused C++ integration, writes and concurrent clients are not evaluated.
- <=128KiB owning filter/cache arrays; member safety index, request features, interpreter/JIT and database cache are separately disclosed, not claimed equal whole-process memory.

## Verify the archived results without RocksDB or datasets

Python 3.10+ standard library:

```bash
python3 src/report16.py --verify-only
python3 src/test_report16.py -v
python3 src/test_archive16.py -v
```

The archive includes all compressed per-query latency arrays. With NumPy available, `python3 src/report16.py --verify-only --latencies` independently recomputes all mean/p50/p95/p99 values. On the experiment host, add `--inputs` to check original input, immutable SST and dependency digests as well.

## Full reruns

The frozen runner is `src/run16.py`. It is resume-oriented and does not rerun completed outputs. A fresh experiment requires a separate output copy, original prepared URL data, query fixtures, generated database and the authorized isolated dependency. Preserve these archived results rather than overwrite them.

On the recorded macOS-arm64/Python 3.12 host, the only additional dependency is `rocksdict==0.3.29`, placed in `.deps/py312` (not the existing conda environment). `.deps`, `inputs` and `db` are ignored by Git; no dependency wheel, SST or source dataset is published. `prepare16.py` generates the fixed request fixtures and database; `build16.py` constructs deployed arrays; `query16.py` performs real queries.

The experiment host's v2 database/dependency directories reference the original round16 immutable snapshot and isolated wheel. Those local symlinks are not needed for offline archival verification and are not committed. Set up real paths in a new rerun workspace.

## Preserved configuration failure

The first campaign in `../round16_rocksdb` is **invalid for its requested Bloom/cache-capacity treatment**. On reopening, top-level options did not configure the default column family. Its 60 answer-correct runs are retained for diagnosis but excluded from valid performance conclusions. V2 corrects option propagation and verifies the effective treatment; no workload, budget, data or candidate was tuned to improve outcomes.

See `plan/design-freeze.md` for the complete protocol. Paper files and previously frozen source files were not edited.

# INVALID FOR THE TARGET DATABASE CONFIGURATION

The initial60-run campaign completed and returned correct answers, but a post-run audit found that the supplied cache/Bloom options were not applied to the default column family when reopening the database. The supplied Cache object's usage was0, both capacity regimes had identical cache counters, and Bloom useful count was0. These timings must NOT be cited as a comparison with enabled native Bloom or1GiB versus8MiB caches. Preserved as a failed-configuration archive; corrected runs are in ../round16_rocksdb_v2.

# Round16: real RocksDB point queries with confirmed-miss feedback

Frozen URL member data, synthetic Zipf/unique negative lookup streams and10% hits. All five methods use real synchronous RocksDB Get results; the negative cache updates only after Get returns None. This is an embedded database integration study, not a production trace or database-network benchmark.

- Direct RocksDB, ordinary BF+cache, shared Gama, RA6, learned-grid Replay.
- Native RocksDB10bits/key Bloom, default compression and caching retained.
- Read-only841.5MiB SST snapshot;1GiB versus8MiB block-cache capacity, full-member warmup before every run, external caches initially empty. OS page cache is not cleared; block misses are not claimed as device reads.
- Three fresh training/selection repetitions and60 fresh serial query processes.
- Individual-query p95/p99, throughput, actual Get counts, backend-confirmed misses, block-cache/Bloom statistics, memory and preparation costs.
-4 integration checks and5 separate2048-query pilots passed. They are not formal performance evidence.

See `plan/design-freeze.md` for all measurement/feedback and memory boundaries.

The user authorized an isolated `rocksdict==0.3.29` wheel under `.deps/py312`; it bundles RocksDB9.8.4. Neither old conda environment was changed. The initial pip invocation selected a Python3.13 wheel; the experiment uses the separately installed Python3.12-compatible wheel, whose digest is frozen. No wheel or generated database is committed.

```bash
# In this directory with the existing data/environment and isolated dependency:
caffeinate -s -i ../../.condaenv/bin/python -u src/run16.py
```

Completed outputs are checked/skipped, partial/error outputs stop without automatic retry. In-place updates or new writes to the database are outside the evaluated semantics. Prior experiment code and paper files remain unchanged.

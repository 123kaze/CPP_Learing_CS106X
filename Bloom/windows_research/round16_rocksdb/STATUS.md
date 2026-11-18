# INVALID FOR THE TARGET DATABASE CONFIGURATION

The initial60-run campaign completed and returned correct answers, but a post-run audit found that the supplied cache/Bloom options were not applied to the default column family when reopening the database. The supplied Cache object's usage was0, both capacity regimes had identical cache counters, and Bloom useful count was0. These timings must NOT be cited as a comparison with enabled native Bloom or1GiB versus8MiB caches. Preserved as a failed-configuration archive; corrected runs are in ../round16_rocksdb_v2.

# Status: formal experiment running

The static RocksDB snapshot and fixed requests are prepared. Four native/backend integration checks and five short real-query pilots passed. Formal source/dependency/cache hashes are frozen; three fresh construction processes and60 serial fresh database-query processes have been launched.

The frozen runner checks returned values and all-member acceptance, actual Get counter agreement, and cache decisions against independent correctness-only simulation. It stops on any failure without retry. Nothing is concluded from the pilot timings.

When complete:

```bash
../../.condaenv/bin/python src/report16.py --inputs --latencies
python3 src/report16.py --verify-only
```

The first command verifies complete records, frozen input/database/dependency hashes and every stored individual-latency percentile before writing the final report. No partial result is published as final performance evidence.

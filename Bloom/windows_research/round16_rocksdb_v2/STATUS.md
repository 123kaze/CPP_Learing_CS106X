# Complete: verified negative result (2026-11-18)

- 3/3 fresh training/selection processes and 60/60 query processes succeeded.
- Actual default-column-family Bloom and block-cache settings verified before each timed run; 1GiB/8MiB residency regimes achieved.
- All returned answers/values, populated-cache member acceptance, Get counters and independent FP checks passed.
- Original data/SST/dependency/source hashes and every stored individual-latency mean/percentile verified.
- 4 online integration tests + 8 effective-configuration rejection tests + 8 data-free archive tests passed.
- RA6 is slower than Direct and BF+cache in all 4 settings and all 12 repetitions. No mean-cost payback versus Direct is estimated. Full unfavorable results are retained.
- The initial campaign in ../round16_rocksdb is invalid for the requested configuration; its records remain clearly labeled and are never substituted for v2 results.
- English report, Chinese conclusion, 60 raw records/logs/statistics and full compressed latency arrays are ready for archival publication.

Paper files and old frozen sources remain unchanged.

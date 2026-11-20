# Direct cell-region table: static first test

Two predetermined features; quantile bins fit on training rows, cell routing/order fitted with full known members and validation negatives. No negative cache, no residual-cost weights, no raw URL n-grams or IP-prefix reconstruction. Table lookup is3bits/cell, but bin edges, layout, array headers and BF navigation are all charged.

| Dataset | Grid | KiB | Table FP | PlainBF FP | Full router bytes | Route ns/key | Route+BF ns/key | Fit/build s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| url | 16×16 | 64 | 79,415 | 106,302 | 696 | 14.9 | 41.7 | 0.0435 |
| url | 16×16 | 128 | 23,692 | 32,377 | 696 | 15.9 | 42.2 | 0.0450 |
| url | 32×32 | 64 | 77,794 | 106,302 | 1240 | 17.4 | 43.9 | 0.0557 |
| url | 32×32 | 128 | 22,995 | 32,377 | 1240 | 17.3 | 48.1 | 0.0580 |
| caida_tcp_flow | 16×16 | 16 | 44,084 | 41,884 | 696 | 14.3 | 27.4 | 0.0150 |
| caida_tcp_flow | 16×16 | 32 | 26,519 | 25,922 | 696 | 14.3 | 34.9 | 0.0168 |
| caida_tcp_flow | 32×32 | 16 | 44,914 | 41,884 | 1240 | 16.6 | 32.5 | 0.0235 |
| caida_tcp_flow | 32×32 | 32 | 27,338 | 25,922 | 1240 | 16.3 | 37.7 | 0.0246 |

## Interpretation

- The table is cheap to evaluate, but these two features lose substantial URL discrimination relative to the round23 full-feature classifiers. All tested TCP configurations still have more FP than plainBF. This is not evidence about all feature partitions or richer routing schemes.
- The claimed “cells ×3bits” is only table payload:256 cells use96 bytes and1024 cells use384 bytes. Complete routers cost696 and1240 bytes including thresholds/layout/headers, before region BF navigation.
- Known-density likelihood-ratio quantization results motivate ratio ordering, but sample smoothing, physical overhead, PASS clipping and integer BF break a simple exact net-KL deployment criterion. Only a smoothed final-region diagnostic KL is recorded; no guarantee of global resource/latency optimality.
- Timings are native per-key computation inside a batch-amortized loop, including two bin searches and packed lookup. They exclude raw feature extraction and key hashing, and are not Python API latency or end-to-end database latency. Cross-round times are a screening comparison, not paired causal speedups.
- Three deterministic builds use identical data and hyperparameters. All cases retained; no evaluation-guided choice of features/grid or retuning. Protocol/source hashes remain frozen.
- Proposal A (residual-cost-weighted training) and C (raw n-grams) are not implemented in this test. The user's requested new experiment branch isolates this work from frozen RA6 and published main.

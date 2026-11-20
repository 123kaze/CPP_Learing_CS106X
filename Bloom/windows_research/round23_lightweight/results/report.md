# Lightweight scorers: first static-filter screen

Two datasets, two budgets each, three fresh deterministic training processes per dataset. All learned scorers use the same frozen FastPLBF allocator; no negative cache or cache-aware training is included. Times are native-loop microbenchmarks with amortized Python call overhead, not database or scalar Python API latency.

## url

| Model | Model bytes incl. headers | Train s | AUC | Fit status |
|---|---:|---:|---:|---|
| LR | 552 | 0.332 | 0.9456 | converged |
| GaussianNB | 984 | 0.032 | 0.8577 | completed |
| Additive16 | 4696 | 2.222 | 0.9814 | stopped_without_convergence |
| MLP8 | 1688 | 1.162 | 0.9843 | stopped_without_convergence |
| Tree1 | 1342 | 0.151 | 0.9754 | completed |
| Tree16 | 11392 | 0.292 | 0.9863 | completed |

| Model | KiB budget | Negative pool FP | Native model+BF ns/query |
|---|---:|---:|---:|
| BF | 64 | 106,302 | 11.0 |
| LR | 64 | 9,218 | 172.1 |
| GaussianNB | 64 | 25,831 | 272.2 |
| Additive16 | 64 | 2,341 | 330.9 |
| MLP8 | 64 | 1,763 | 240.8 |
| Tree1 | 64 | 5,438 | 285.0 |
| Tree16 | 64 | 1,357 | 560.4 |
| BF | 128 | 32,377 | 14.0 |
| LR | 128 | 2,403 | 166.6 |
| GaussianNB | 128 | 7,373 | 277.0 |
| Additive16 | 128 | 514 | 337.7 |
| MLP8 | 128 | 364 | 248.3 |
| Tree1 | 128 | 1,591 | 209.7 |
| Tree16 | 128 | 205 | 579.2 |
## caida_tcp_flow

| Model | Model bytes incl. headers | Train s | AUC | Fit status |
|---|---:|---:|---:|---|
| LR | 168 | 0.012 | 0.4999 | converged |
| GaussianNB | 216 | 0.006 | 0.4999 | completed |
| Additive16 | 728 | 0.032 | 0.5406 | converged |
| MLP8 | 408 | 0.230 | 0.4999 | converged |
| Tree1 | 1342 | 0.018 | 0.5473 | completed |
| Tree16 | 11392 | 0.035 | 0.5567 | completed |

| Model | KiB budget | Negative pool FP | Native model+BF ns/query |
|---|---:|---:|---:|
| BF | 16 | 41,884 | 5.9 |
| LR | 16 | 44,705 | 39.4 |
| GaussianNB | 16 | 44,898 | 44.2 |
| Additive16 | 16 | 45,758 | 56.2 |
| MLP8 | 16 | 45,139 | 48.4 |
| Tree1 | 16 | 46,135 | 95.2 |
| Tree16 | 16 | 61,532 | 288.7 |
| BF | 32 | 25,922 | 7.8 |
| LR | 32 | 27,226 | 44.4 |
| GaussianNB | 32 | 27,188 | 51.8 |
| Additive16 | 32 | 27,238 | 61.8 |
| MLP8 | 32 | 27,358 | 55.7 |
| Tree1 | 32 | 27,466 | 102.1 |
| Tree16 | 32 | 37,212 | 317.0 |

## Boundaries

- URL Additive16/MLP8 reached the fixed optimization limit without convergence; they are not best-tuned representatives. The records retain status and objective; no retries/hyperparameter changes followed the outcomes.
- GaussianNB has different model assumptions and training loss. Tree1/16 are fixed controls, not the original200-prefix search. All three training runs use the same seed/data and are timing repeats, not statistical generalization trials.
- Model bytes include required standardization/bin edges and owning-array headers; common request features/prehashed keys and interpreter/JIT state are excluded. PureBF uses its strongest one-array representation. Filter metadata is not hidden.
- Native model+BF loop includes per-request feature normalization/binning/tree traversal and BF probes. It excludes raw URL extraction and hash calculation for all methods. No precomputed scores/flags substitute timed queries. Percentile scalar API latency is not measured.
- Smaller models can trade additional FP for lower memory and inference cost; these data do not establish database speedup or a universally superior model. TCP-only uses the same stored address encoding, whose lack of information is not fixed by changing classifiers.
- This new experiment branch does not modify frozen RA6, cache prediction, prior papers, published historical results or the existing dependency environment. Direct partition tables and cost-weighted training are separate follow-on hypotheses.

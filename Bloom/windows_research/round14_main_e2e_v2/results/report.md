# Round 14: optimized end-to-end timings on the eight main-table settings

72 fresh processes: 8 settings × 3 repetitions × original G-PLBF / RA6-loop / RA6-leaf. All 24 RA6 pairs have identical model and 14-prefix score digests, selected configurations, filter payloads and native query counts. All methods match their corresponding round-7 archived configurations/counts. The separate 3-process pilot is excluded.

Times are medians of 3 runs in seconds. Ratios are medians of the 3 paired ratios, not ratios of median times.

## Construction

| Dataset | KiB | Original ready s | Loop ready s | Leaf ready s | Loop/leaf speedup | Leaf/original cost ratio |
|---|---:|---:|---:|---:|---:|---:|
| caida_flow | 24 | 0.455 | 10.992 | 4.828 | 2.313× | 10.375 |
| url | 128 | 1.691 | 17.272 | 8.558 | 2.034× | 4.996 |
| mawi2020_flow | 24 | 0.222 | 8.690 | 4.099 | 2.095× | 18.514 |
| mawi2021_flow | 24 | 0.214 | 5.609 | 3.057 | 1.824× | 14.227 |
| mawi2022_flow | 24 | 0.203 | 6.942 | 3.414 | 2.033× | 16.763 |
| caida | 256 | 8.516 | 85.517 | 32.231 | 2.625× | 3.782 |
| shalla | 1024 | 35.783 | 86.282 | 34.309 | 2.500× | 0.964 |
| cod | 1024 | 127.795 | 181.287 | 105.865 | 1.712× | 0.828 |

## Full negative tail and construction plus tail

| Dataset | Original FP | Leaf FP | Original tail s | Leaf tail s | Tail speedup | Original ready+tail s | Leaf ready+tail s | Leaf/original total ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| caida_flow | 2478667 | 376911 | 15.365 | 0.627 | 25.262× | 15.818 | 5.455 | 0.345 |
| url | 5935 | 159 | 33.882 | 5.766 | 5.876× | 35.571 | 14.324 | 0.403 |
| mawi2020_flow | 339989 | 17410 | 17.893 | 0.525 | 33.862× | 18.114 | 4.635 | 0.256 |
| mawi2021_flow | 804380 | 10347 | 10.303 | 0.261 | 39.550× | 10.521 | 3.318 | 0.315 |
| mawi2022_flow | 503966 | 19010 | 8.889 | 0.236 | 37.690× | 9.092 | 3.650 | 0.402 |
| caida | 362760 | 29793 | 21.058 | 19.908 | 1.059× | 29.574 | 52.139 | 1.774 |
| shalla | 352067 | 61474 | 35.134 | 4.010 | 8.575× | 72.115 | 38.318 | 0.548 |
| cod | 3260 | 45 | 50.104 | 28.377 | 1.765× | 177.898 | 134.248 | 0.755 |

## Mixed-query timings

| Dataset | Mode | Original s | Loop s | Leaf s | Original FP | Leaf FP | All FN |
|---|---|---:|---:|---:|---:|---:|---:|
| caida_flow | mixed_batch | 0.6989 | 0.0290 | 0.0311 | 99659 | 16716 | 0 |
| caida_flow | mixed_scalar | 0.3927 | 0.0560 | 0.0581 | 10125 | 1945 | 0 |
| url | mixed_batch | 0.9172 | 0.1501 | 0.1507 | 144 | 15 | 0 |
| url | mixed_scalar | 0.4000 | 0.0729 | 0.0688 | 15 | 2 | 0 |
| mawi2020_flow | mixed_batch | 0.7639 | 0.0257 | 0.0238 | 13560 | 811 | 0 |
| mawi2020_flow | mixed_scalar | 0.3715 | 0.0562 | 0.0529 | 1369 | 140 | 0 |
| mawi2021_flow | mixed_batch | 0.8102 | 0.0213 | 0.0204 | 52772 | 793 | 0 |
| mawi2021_flow | mixed_scalar | 0.3721 | 0.0528 | 0.0528 | 7163 | 128 | 0 |
| mawi2022_flow | mixed_batch | 0.7940 | 0.0220 | 0.0213 | 44492 | 1745 | 0 |
| mawi2022_flow | mixed_scalar | 0.3687 | 0.0528 | 0.0526 | 6203 | 228 | 0 |
| caida | mixed_batch | 0.5391 | 0.5969 | 0.6033 | 8784 | 990 | 0 |
| caida | mixed_scalar | 0.3750 | 0.1129 | 0.1164 | 820 | 129 | 0 |
| shalla | mixed_batch | 0.9776 | 0.1053 | 0.1001 | 8303 | 3773 | 0 |
| shalla | mixed_scalar | 0.4295 | 0.0630 | 0.0646 | 823 | 556 | 0 |
| cod | mixed_batch | 1.2942 | 0.8051 | 0.8105 | 74 | 5 | 0 |
| cod | mixed_scalar | 0.4862 | 0.1371 | 0.1442 | 8 | 3 | 0 |

## Process peak RSS

| Dataset | Original GiB | Loop GiB | Leaf GiB | Paired leaf/loop median |
|---|---:|---:|---:|---:|
| caida_flow | 0.323 | 0.503 | 0.591 | 1.182 |
| url | 0.732 | 0.814 | 0.935 | 1.154 |
| mawi2020_flow | 0.320 | 0.498 | 0.575 | 1.162 |
| mawi2021_flow | 0.237 | 0.396 | 0.444 | 1.123 |
| mawi2022_flow | 0.247 | 0.420 | 0.463 | 1.091 |
| caida | 2.103 | 2.204 | 2.650 | 1.217 |
| shalla | 3.101 | 2.180 | 2.399 | 1.100 |
| cod | 7.106 | 4.529 | 4.258 | 1.029 |

## Interpretation and limitations

- `ready` includes training, prefix scoring/input preparation, selection and executable-filter construction. Reading data, JIT warm-up, query-input assembly, hash/correctness checks and service queries are excluded and recorded separately. `process_wall_s` includes these and is not construction time.
- Prefix scoring is the only algorithm-path change. Three repetitions are timing repetitions of the same data, not independent dataset samples; no new significance claim is made.
- This round freshly measures the original implementation in the same serial campaign. Original G-PLBF still uses its own pickle/bitmap accounting and Python/LightGBM/bloom_filter path; RA6 uses compact arrays/Numba. Matching nominal budgets is not proof of matching physical bytes, and this is not a same-kernel algorithm ablation.
- The verified-prefix cache still requires an out-of-budget 8-byte-per-member index. Whole-process RSS is not deployment memory. A bounded leaf-ID matrix does not imply lower RSS.
- Paired RSS-ratio medians need not equal the ratio of the two RSS medians (notably COD). The query implementation is unchanged: changes in query timings across campaigns are remeasurements, not evidence that prefix-score preparation speeds up service queries.
- The original UDP-member/TCP-negative trace construction is unchanged. These results do not replace the less favorable TCP-only comparison with ordinary BF+cache.
- Full-tail evaluation starts from an empty cache. Mixed batch uses 200,000 queries at batch=1000; mixed scalar uses the first 20,000 at batch=1. These measurements must not be pooled.
- Construction-plus-tail is measured computation only: it excludes database, network and backing-store lookup latency. Each total is computed within a run before taking its median.
- The first round-14 launcher failed during input-path preflight before any training started. The failed version/logs remain in `../round14_main_e2e`; v2 corrects only the manifest cache path. No failed or slow measured repetition was discarded.
- `timing_summary.json` retains every paired ratio and its range; `timing_rows.csv` retains every run. Data-free verification checks archived results and available sources; `--inputs` additionally requires all original sources and hashes all raw inputs. No upstream code is redistributed to make verification pass.

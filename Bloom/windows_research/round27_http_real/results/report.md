# Real HTTP missing-resource requests: full results

NASA KSC July/August1995. Real chronological GET404 requests, not synthesized popularity. Model sees20lexical URL/path features, no protocol/status/response-size/time/frequency features. All5methods share each physical budget and held-out negative tail.

**Scope:** retrospective static-stable-resource subset. The full month defines the successful-resource catalog and excludes success/404 conflicts. Therefore this is NOT a prospective mutable-site or real-backend latency benchmark. Train/validation negative keys are prefix-only and disjoint from query-pool keys; fresh tail keys are not used to train.

## Data construction and exclusions

| Month | Parsed GET | Stable members | Stable absent keys | Actual retained404requests | Conflicting keys excluded |404requests excluded for conflicts |
|---|---:|---:|---:|---:|---:|---:|
| nasa_jul95 | 1886318 | 7110 | 2279 | 10575 | 29 | 195 |
| nasa_aug95 | 1564912 | 6464 | 1663 | 9872 | 14 | 70 |

## Learning and held-out diagnostics

| Month | Seed | Learn requests/distinct | Tail requests/distinct |16-tree AUC |200-tree AUC | Negative keys sharing exact feature vectors with members |
|---|---:|---|---|---:|---:|---:|
| nasa_jul95 | 2701 | 2049/496 | 6883/1880 | 0.8779 | 0.8596 | 346 |
| nasa_jul95 | 2702 | 1891/491 | 6914/1871 | 0.8925 | 0.8795 | 343 |
| nasa_jul95 | 2703 | 2140/496 | 7156/1868 | 0.9013 | 0.8840 | 338 |
| nasa_aug95 | 2701 | 2238/483 | 5720/1245 | 0.8617 | 0.8041 | 303 |
| nasa_aug95 | 2702 | 2283/479 | 6402/1239 | 0.8891 | 0.8532 | 311 |
| nasa_aug95 | 2703 | 2457/479 | 6639/1238 | 0.8650 | 0.8549 | 303 |

## All budgets: medianFP across3paired split/hash seeds

These are conditional repetitions of the same logs, not6independent workloads. Medians are descriptive; raw paired counts and ratios are in rows.csv. No >=30FP inclusion threshold.

| Month | KiB | Gama | Replay | RA-global | RA-PLBF-GT19 | BF+Cache | RA/BF+Cache median paired ratio | RA/Replay median paired ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nasa_jul95 | 4 | 3217 | 1731 | 1914 | 1480 | 405 | 3.4606 | 0.8150 |
| nasa_jul95 | 8 | 522 | 154 | 154 | 103 | 23 | 3.6250 | 0.6259 |
| nasa_jul95 | 16 | 1 | 1 | 1 | 2 | 0 | 3.0000 | 1.0000 |
| nasa_aug95 | 4 | 3926 | 1051 | 1066 | 776 | 188 | 4.1111 | 0.7376 |
| nasa_aug95 | 8 | 1104 | 98 | 73 | 52 | 14 | 3.2667 | 0.5657 |
| nasa_aug95 | 16 | 0 | 0 | 0 | 0 | 0 | 1.0000 | 1.0000 |

## Interpretation and boundaries

- The original candidate grid remains learned-only. The no-model method is an explicit comparator, not a hidden fallback. No repetition-to-Gama property is asserted for an expanded selector.
- Region repetition diagnostics use each learned candidate’s fixed regions and preserve both learning and tail descriptive values. Tail values are reported only after selection, not used to pick configurations.
- AUC/feature overlap establish a non-protocol classification task, but do not by themselves establish a learned-filter or reweighting advantage. Compare RA to BF+Cache AND to Replay/RA-global at each matched budget; retain all losses.
- Memory breakdown includes real model arrays, BF bytes, layout/header overhead, allocated cache and unused bytes. The separate8*n backend verification index remains outside the filter budget; fp64 semantics are audited separately in round29.
- Training/scoring/index/build/selection/replay wall times are recorded. One timed execution per configuration with shared preparation is NOT a controlled latency/speedup experiment. Native per-query feature extraction/backend Get timing is not measured here.
- These old NASA logs are small, historical and only one site. They cannot alone establish modern production applicability. Sparse404counts and fitting the working set in BF+Cache can make model overhead unhelpful. Such outcomes are not excluded.

Sources: https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html ; August mirror https://github.com/COM6012/ScalableML/blob/master/Data/NASA_access_log_Aug95.gz . Download receipts retain gzip CRC checks and SHA256; failed partial downloads are not used as complete data.

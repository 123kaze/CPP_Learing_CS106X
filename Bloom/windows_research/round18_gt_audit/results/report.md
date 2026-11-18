# Frozen Good–Turing count audit: real inputs, no repaired method

The audit regenerates actual learning streams, verifies their full-base hashes against archived round13 records, and calls the frozen summarize function. No model is trained, no candidate is reranked, and no FP result is replaced. Budget cases share learning streams:1146 main cases plus4 MAWI-24 cases correspond to325 dataset/workload/seed groups. The16 TCP-only settings are a separately labeled supplement.

| Cohort | Cases | Any missing-next-bin trigger | All-singleton cases | Non-singleton triggers | Total mass collapse |
|---|---:|---:|---:|---:|---:|
| main | 1146 | 154 | 140 | 14 | 0 |
| holdout | 4 | 0 | 0 | 0 | 0 |
| tcp_supplement | 16 | 0 | 0 | 0 | 0 |

## Actual real-trace learning prefixes

| Dataset | Learning negative queries | Gap bins | Affected queries | Original seen+unseen mass |
|---|---:|---|---:|---:|
| caida_flow | 1,443,950 | [] | 0 | 1.0087392223 |
| mawi2020_flow | 1,445,151 | [] | 0 | 1.0014489835 |
| mawi2021_flow | 857,343 | [] | 0 | 1.0013961740 |
| mawi2022_flow | 741,279 | [] | 0 | 1.0039013651 |
| mawi2024_flow | 497,414 | [] | 0 | 1.0041715754 |
| caida_tcp_flow | 141,676 | [] | 0 | 1.0377763347 |
| mawi2020_tcp_flow | 89,433 | [] | 0 | 1.0055348697 |
| mawi2021_tcp_flow | 80,564 | [] | 0 | 1.0119159923 |
| mawi2022_tcp_flow | 121,238 | [] | 0 | 1.0049489434 |

## Triggered streams with repeated keys

| Dataset | Workload | Seed | Budgets | Missing-next bins | Keys affected | Learning queries affected | Query share |
|---|---|---:|---|---|---:|---:|---:|
| cod | uniform-10万 | 0 | [1024, 256, 4096] | [5] | 1 | 5 | 2e-06 |
| url | uniform-10万 | 0 | [128, 256, 64] | [5] | 1 | 5 | 2e-06 |
| caida | uniform-10万 | 2 | [1024, 128, 2048, 256] | [5] | 1 | 5 | 2e-06 |
| shalla | uniform-10万 | 0 | [1024, 2048, 256, 4096] | [5] | 1 | 5 | 2e-06 |

## Conclusions allowed by this audit

- Missing-next-bin degeneration is real: equal2–5 repeats per key produces zero seen rates and zero unseen mass. An all-singleton prefix is different: seen rates are zero but unseen mass is1 under the original construction.
- Literal fallback for every c<=5 makes an all-singleton prefix assign seen mass1 plus unseen mass1. Simply falling back to c is therefore NOT an unconditional repair of the original contract.
- Preserving the all-singleton special case avoids that particular change, but does not establish calibrated probabilities. The mixed-count example [1,1,2,2] gives total mass4/3 after fallback; [1,2,3,4,5,6] already exceeds1 with no missing-next bin. Missing-bin repair and probability normalization are distinct questions.
- For untriggered inputs the diagnostic fallback array is bit-identical, and its hash is recorded. This is not a new-method rerun or a proof that every existing experiment is unchanged after arbitrary smoothing/renormalization. Changed statistics must be followed through candidate selection and held-out FP before claiming negligible effectiveness impact.
- Main/holdout quality streams contain only neg_test keys by construction; raw labels are excluded before summarize. The summarize function itself has no member-label check and will accept arbitrary integer keys, so it cannot by itself enforce mixed-query semantics.
- Real feedback can reuse a label from a Get that would already occur; this does not make acquiring all negative-learning labels free. Filtered-out requests never call the backend, and logging backend misses alone samples a different stream. Round16 explicitly measures actual learning Gets; source selection costs and label/logging costs must be separated.
- No claims here about unchanged full-table FP totals, the718/748 comparison, repaired selection speedups or a submission-date decision. This audit diagnoses counts, not method quality. Any affected MAWI-24 reselection would be post-hoc, preserving the original frozen holdout results.

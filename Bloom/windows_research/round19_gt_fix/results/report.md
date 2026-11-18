# Repeated-frequency-gap repair: verified impact

New round19 repair:retain c only for gt=True,2<=c<=5 and empty N[c+1]. Singleton, counts above5 and gt=False remain byte-identical. This is a post-freeze local repair, not SGT, normalization, a new zero-tree rule or an unbiasedness/optimality claim.

Actual inputs:all1146 main cases checked;1132 unchanged statistic arrays,14 changed cases. All4 MAWI-24 budgets unchanged. Expanded audit:51 actual supplementary learning inputs unchanged.

## Old versus repaired main summaries (original748 eligible cases per format)

| Cache | Reference | Old median | Repaired median | Old win/tie/loss | Repaired win/tie/loss |
|---|---|---:|---:|---|---|
| index | bf_cache_fp | 0.015410907 | 0.015410907 | 718/0/30 | 718/0/30 |
| index | gama_fp | 0.0879614343 | 0.0879614343 | 635/110/3 | 635/110/3 |
| index | replay_fp | 0.999461344 | 0.999481526 | 382/24/342 | 381/24/343 |
| index | reference_fp | 1.00514014 | 1.00490973 | 293/30/425 | 293/30/425 |
| fp64 | bf_cache_fp | 0.0159510177 | 0.0159510177 | 718/0/30 | 718/0/30 |
| fp64 | gama_fp | 0.0973855527 | 0.0973855527 | 633/110/5 | 633/110/5 |
| fp64 | replay_fp | 0.995538357 | 0.995615508 | 413/14/321 | 412/14/322 |
| fp64 | reference_fp | 1.07226107 | 1.07226107 | 143/27/578 | 143/27/578 |

## Changes in all affected RA-family checks

- selected_method_comparisons: 168
- selected_fp_changes: 51
- selected_configuration_changes: 9
- selected_payload_changes: 82
- selected_prediction_changes: 115
- warm_fp_changes: 3
- candidate_records: 1779
- candidate_fp_changes: 1065
- candidate_prediction_changes: 1779
- rank_top10_changes: 0

## Affected-case selected results

| Dataset | KiB | Seed | Cache | Method | Old FP | Repaired FP | Same configuration | Identical BF payload |
|---|---:|---:|---|---|---:|---:|---|---|
| cod | 256 | 0 | index | RA6-top3 | 534 | 532 | True | False |
| cod | 256 | 0 | index | RA6 | 534 | 532 | True | False |
| cod | 256 | 0 | index | RA6-top10 | 534 | 532 | True | False |
| cod | 256 | 0 | index | RA4 | 534 | 532 | True | False |
| cod | 256 | 0 | index | RA4-noRepeat | 653 | 653 | True | True |
| cod | 256 | 0 | index | RA4-noSA | 4687 | 4687 | True | True |
| cod | 256 | 0 | index | RA4-noGT | 532 | 532 | True | True |
| cod | 256 | 0 | index | RA4-mix0.5 | 534 | 532 | True | False |
| cod | 256 | 0 | index | RA4-mix1 | 534 | 532 | True | False |
| cod | 256 | 0 | index | RA4-Table | 10572 | 10754 | True | False |
| cod | 256 | 0 | index | RA-global | 563 | 563 | True | True |
| cod | 1024 | 0 | index | RA6-top3 | 3 | 3 | True | False |
| cod | 1024 | 0 | index | RA6 | 3 | 3 | True | False |
| cod | 1024 | 0 | index | RA6-top10 | 2 | 2 | True | False |
| cod | 1024 | 0 | index | RA4 | 3 | 3 | True | False |
| cod | 1024 | 0 | index | RA4-noRepeat | 3 | 3 | True | True |
| cod | 1024 | 0 | index | RA4-noSA | 3 | 3 | True | False |
| cod | 1024 | 0 | index | RA4-noGT | 3 | 3 | True | True |
| cod | 1024 | 0 | index | RA4-mix0.5 | 3 | 3 | True | False |
| cod | 1024 | 0 | index | RA4-mix1 | 3 | 3 | True | False |
| cod | 1024 | 0 | index | RA4-Table | 155 | 218 | True | False |
| cod | 1024 | 0 | index | RA-global | 6 | 6 | True | True |
| cod | 4096 | 0 | index | RA6-top3 | 0 | 0 | True | False |
| cod | 4096 | 0 | index | RA6 | 0 | 0 | True | False |
| cod | 4096 | 0 | index | RA6-top10 | 0 | 0 | True | False |
| cod | 4096 | 0 | index | RA4 | 0 | 0 | True | False |
| cod | 4096 | 0 | index | RA4-noRepeat | 0 | 0 | True | True |
| cod | 4096 | 0 | index | RA4-noSA | 0 | 0 | True | False |
| cod | 4096 | 0 | index | RA4-noGT | 0 | 0 | True | True |
| cod | 4096 | 0 | index | RA4-mix0.5 | 0 | 0 | True | False |
| cod | 4096 | 0 | index | RA4-mix1 | 0 | 0 | True | False |
| cod | 4096 | 0 | index | RA4-Table | 0 | 0 | True | False |
| cod | 4096 | 0 | index | RA-global | 0 | 0 | True | True |
| cod | 256 | 0 | fp64 | RA6 | 639 | 636 | True | False |
| cod | 1024 | 0 | fp64 | RA6 | 2 | 2 | True | False |
| cod | 4096 | 0 | fp64 | RA6 | 0 | 0 | True | False |
| url | 64 | 0 | index | RA6-top3 | 938 | 938 | True | True |
| url | 64 | 0 | index | RA6 | 836 | 836 | True | True |
| url | 64 | 0 | index | RA6-top10 | 836 | 836 | True | True |
| url | 64 | 0 | index | RA4 | 1153 | 1153 | True | True |
| url | 64 | 0 | index | RA4-noRepeat | 842 | 842 | True | True |
| url | 64 | 0 | index | RA4-noSA | 4527 | 4527 | True | True |
| url | 64 | 0 | index | RA4-noGT | 1153 | 1153 | True | True |
| url | 64 | 0 | index | RA4-mix0.5 | 1153 | 1153 | True | True |
| url | 64 | 0 | index | RA4-mix1 | 1153 | 1153 | True | True |
| url | 64 | 0 | index | RA4-Table | 10572 | 10572 | True | True |
| url | 64 | 0 | index | RA-global | 949 | 949 | True | True |
| url | 128 | 0 | index | RA6-top3 | 48 | 48 | True | True |
| url | 128 | 0 | index | RA6 | 48 | 48 | True | True |
| url | 128 | 0 | index | RA6-top10 | 48 | 48 | True | True |
| url | 128 | 0 | index | RA4 | 48 | 48 | True | True |
| url | 128 | 0 | index | RA4-noRepeat | 68 | 68 | True | True |
| url | 128 | 0 | index | RA4-noSA | 113 | 113 | True | True |
| url | 128 | 0 | index | RA4-noGT | 48 | 48 | True | True |
| url | 128 | 0 | index | RA4-mix0.5 | 48 | 48 | True | True |
| url | 128 | 0 | index | RA4-mix1 | 48 | 48 | True | True |
| url | 128 | 0 | index | RA4-Table | 1948 | 2023 | True | False |
| url | 128 | 0 | index | RA-global | 52 | 52 | True | True |
| url | 256 | 0 | index | RA6-top3 | 1 | 1 | True | True |
| url | 256 | 0 | index | RA6 | 1 | 1 | True | True |
| url | 256 | 0 | index | RA6-top10 | 1 | 1 | True | True |
| url | 256 | 0 | index | RA4 | 2 | 2 | True | True |
| url | 256 | 0 | index | RA4-noRepeat | 0 | 0 | True | True |
| url | 256 | 0 | index | RA4-noSA | 2 | 2 | True | True |
| url | 256 | 0 | index | RA4-noGT | 2 | 2 | True | True |
| url | 256 | 0 | index | RA4-mix0.5 | 2 | 2 | True | True |
| url | 256 | 0 | index | RA4-mix1 | 2 | 2 | True | True |
| url | 256 | 0 | index | RA4-Table | 160 | 160 | True | True |
| url | 256 | 0 | index | RA-global | 2 | 2 | True | True |
| url | 64 | 0 | fp64 | RA6 | 1229 | 1229 | True | True |
| url | 128 | 0 | fp64 | RA6 | 50 | 50 | True | True |
| url | 256 | 0 | fp64 | RA6 | 0 | 0 | True | False |
| caida | 128 | 2 | index | RA6-top3 | 35388 | 35388 | True | True |
| caida | 128 | 2 | index | RA6 | 35388 | 35388 | True | True |
| caida | 128 | 2 | index | RA6-top10 | 35388 | 35388 | True | True |
| caida | 128 | 2 | index | RA4 | 35388 | 35388 | True | True |
| caida | 128 | 2 | index | RA4-noRepeat | 36453 | 36453 | True | True |
| caida | 128 | 2 | index | RA4-noSA | 54018 | 54018 | True | True |
| caida | 128 | 2 | index | RA4-noGT | 35388 | 35388 | True | True |
| caida | 128 | 2 | index | RA4-mix0.5 | 35388 | 35388 | True | True |
| caida | 128 | 2 | index | RA4-mix1 | 35388 | 35388 | True | True |
| caida | 128 | 2 | index | RA4-Table | 91860 | 91860 | True | True |
| caida | 128 | 2 | index | RA-global | 35087 | 35087 | True | True |
| caida | 256 | 2 | index | RA6-top3 | 1591 | 1591 | True | True |
| caida | 256 | 2 | index | RA6 | 1591 | 1591 | True | True |
| caida | 256 | 2 | index | RA6-top10 | 1591 | 1591 | True | True |
| caida | 256 | 2 | index | RA4 | 1675 | 1675 | True | True |
| caida | 256 | 2 | index | RA4-noRepeat | 1809 | 1809 | True | True |
| caida | 256 | 2 | index | RA4-noSA | 4582 | 4582 | True | True |
| caida | 256 | 2 | index | RA4-noGT | 1675 | 1675 | True | True |
| caida | 256 | 2 | index | RA4-mix0.5 | 1675 | 1675 | True | True |
| caida | 256 | 2 | index | RA4-mix1 | 1675 | 1675 | True | True |
| caida | 256 | 2 | index | RA4-Table | 24223 | 24223 | True | True |
| caida | 256 | 2 | index | RA-global | 1703 | 1703 | True | True |
| caida | 1024 | 2 | index | RA6-top3 | 48 | 48 | True | False |
| caida | 1024 | 2 | index | RA6 | 48 | 48 | True | False |
| caida | 1024 | 2 | index | RA6-top10 | 48 | 48 | True | False |
| caida | 1024 | 2 | index | RA4 | 66 | 66 | True | True |
| caida | 1024 | 2 | index | RA4-noRepeat | 48 | 47 | True | False |
| caida | 1024 | 2 | index | RA4-noSA | 50 | 50 | True | False |
| caida | 1024 | 2 | index | RA4-noGT | 66 | 66 | True | True |
| caida | 1024 | 2 | index | RA4-mix0.5 | 66 | 66 | True | True |
| caida | 1024 | 2 | index | RA4-mix1 | 66 | 66 | True | True |
| caida | 1024 | 2 | index | RA4-Table | 322 | 322 | True | False |
| caida | 1024 | 2 | index | RA-global | 43 | 43 | True | True |
| caida | 2048 | 2 | index | RA6-top3 | 1 | 1 | True | False |
| caida | 2048 | 2 | index | RA6 | 1 | 1 | True | False |
| caida | 2048 | 2 | index | RA6-top10 | 0 | 1 | False | False |
| caida | 2048 | 2 | index | RA4 | 1 | 1 | True | False |
| caida | 2048 | 2 | index | RA4-noRepeat | 1 | 1 | True | True |
| caida | 2048 | 2 | index | RA4-noSA | 1 | 1 | True | False |
| caida | 2048 | 2 | index | RA4-noGT | 1 | 1 | True | True |
| caida | 2048 | 2 | index | RA4-mix0.5 | 1 | 1 | True | False |
| caida | 2048 | 2 | index | RA4-mix1 | 1 | 1 | True | False |
| caida | 2048 | 2 | index | RA4-Table | 71 | 71 | True | True |
| caida | 2048 | 2 | index | RA-global | 1 | 1 | True | True |
| caida | 128 | 2 | fp64 | RA6 | 79167 | 79167 | True | True |
| caida | 256 | 2 | fp64 | RA6 | 2147 | 2147 | True | True |
| caida | 1024 | 2 | fp64 | RA6 | 49 | 49 | True | True |
| caida | 2048 | 2 | fp64 | RA6 | 1 | 1 | True | False |
| shalla | 256 | 0 | index | RA6-top3 | 304089 | 305715 | True | False |
| shalla | 256 | 0 | index | RA6 | 304089 | 305715 | True | False |
| shalla | 256 | 0 | index | RA6-top10 | 304089 | 305715 | True | False |
| shalla | 256 | 0 | index | RA4 | 323993 | 326172 | True | False |
| shalla | 256 | 0 | index | RA4-noRepeat | 319614 | 317445 | True | False |
| shalla | 256 | 0 | index | RA4-noSA | 320503 | 317527 | True | False |
| shalla | 256 | 0 | index | RA4-noGT | 326172 | 326172 | True | True |
| shalla | 256 | 0 | index | RA4-mix0.5 | 323993 | 326172 | True | False |
| shalla | 256 | 0 | index | RA4-mix1 | 323993 | 326172 | True | False |
| shalla | 256 | 0 | index | RA4-Table | 424694 | 426199 | True | False |
| shalla | 256 | 0 | index | RA-global | 305330 | 305330 | True | True |
| shalla | 1024 | 0 | index | RA6-top3 | 8218 | 8001 | True | False |
| shalla | 1024 | 0 | index | RA6 | 8218 | 8001 | True | False |
| shalla | 1024 | 0 | index | RA6-top10 | 8218 | 8001 | True | False |
| shalla | 1024 | 0 | index | RA4 | 8229 | 8288 | True | False |
| shalla | 1024 | 0 | index | RA4-noRepeat | 8103 | 8278 | True | False |
| shalla | 1024 | 0 | index | RA4-noSA | 29561 | 29505 | True | False |
| shalla | 1024 | 0 | index | RA4-noGT | 8288 | 8288 | True | True |
| shalla | 1024 | 0 | index | RA4-mix0.5 | 8229 | 8288 | True | False |
| shalla | 1024 | 0 | index | RA4-mix1 | 8229 | 8288 | True | False |
| shalla | 1024 | 0 | index | RA4-Table | 102638 | 102394 | True | False |
| shalla | 1024 | 0 | index | RA-global | 8143 | 8143 | True | True |
| shalla | 2048 | 0 | index | RA6-top3 | 1444 | 1415 | True | False |
| shalla | 2048 | 0 | index | RA6 | 1444 | 1415 | True | False |
| shalla | 2048 | 0 | index | RA6-top10 | 1407 | 1415 | False | False |
| shalla | 2048 | 0 | index | RA4 | 1533 | 1499 | True | False |
| shalla | 2048 | 0 | index | RA4-noRepeat | 1487 | 1326 | True | False |
| shalla | 2048 | 0 | index | RA4-noSA | 8941 | 8505 | True | False |
| shalla | 2048 | 0 | index | RA4-noGT | 1499 | 1499 | True | True |
| shalla | 2048 | 0 | index | RA4-mix0.5 | 1533 | 1499 | True | False |
| shalla | 2048 | 0 | index | RA4-mix1 | 1533 | 1499 | True | False |
| shalla | 2048 | 0 | index | RA4-Table | 24705 | 24755 | True | False |
| shalla | 2048 | 0 | index | RA-global | 1467 | 1467 | True | True |
| shalla | 4096 | 0 | index | RA6-top3 | 66 | 70 | False | False |
| shalla | 4096 | 0 | index | RA6 | 66 | 64 | False | False |
| shalla | 4096 | 0 | index | RA6-top10 | 64 | 64 | False | False |
| shalla | 4096 | 0 | index | RA4 | 79 | 94 | True | False |
| shalla | 4096 | 0 | index | RA4-noRepeat | 81 | 75 | False | False |
| shalla | 4096 | 0 | index | RA4-noSA | 92 | 72 | True | False |
| shalla | 4096 | 0 | index | RA4-noGT | 94 | 94 | True | True |
| shalla | 4096 | 0 | index | RA4-mix0.5 | 79 | 94 | True | False |
| shalla | 4096 | 0 | index | RA4-mix1 | 79 | 94 | True | False |
| shalla | 4096 | 0 | index | RA4-Table | 1938 | 1967 | True | False |
| shalla | 4096 | 0 | index | RA-global | 76 | 76 | True | True |
| shalla | 256 | 0 | fp64 | RA6 | 648372 | 657521 | True | False |
| shalla | 1024 | 0 | fp64 | RA6 | 9650 | 10085 | False | False |
| shalla | 2048 | 0 | fp64 | RA6 | 1547 | 1517 | False | False |
| shalla | 4096 | 0 | fp64 | RA6 | 70 | 69 | False | False |

## Verification and limits

- reference_fp is the original eligibility/Hindsight-or-Replay reference. For fp64 it retains the old indexed reference and is a legacy diagnostic, NOT a same-format comparator; use replay_fp for the same-format Replay comparison. Original cluster-significance tests and all paper tables have not been recomputed by this report.
- The runtime hook is restored on success/error and frozen source hashes are checked. A new adapter owns outputs and distinguishes old-archive reproduction from repaired results; old files are never overwritten and stale old-result assertions are not used to force repaired equality.
- All selected affected structures are actually evaluated on the original tails and compared by configuration, reconstructed packed BF payload and full-pool flags. Warm-cache results, all indexed GT ablations, top3/5/10 and fp64 RA6 are included.
- E3 candidates with identical full-pool flags and cache bytes on the same stream reuse archived FP counts with an explicit deterministic-equivalence justification. Candidates whose flags change undergo new tail replay. Prediction and rank changes are retained separately from unchanged winner FP; “all results unchanged” is not inferred just from equal main totals.
- Unaffected rows retain archive provenance, justified by byte-identical statistic fields and unchanged remaining inputs/code. They are not relabeled as1132 newly executed filters. Original holdout records remain frozen; no revised holdout has been substituted.
- Supplemental coverage includes E10 learning shares, E11 learning prefixes, paper-source once/Zipf, old E5 scaling, round7/14 compressed inputs, round15 up to100M and TCP-only. E4/e789 use the covered main25% prefixes; round12 cost aggregation does not itself execute the counter.
- This patch prevents the missing-next-bin repeated-count collapse only. Boundary discontinuity, nonmonotone adjusted counts, singleton uncertainty and non-unit total mass remain. It is not proof that this estimator is best among SGT/parametric/nonparametric alternatives.
- Existing timing figures describe the original frozen implementation. No new speedup measurement is claimed here; diagnostic rerun wall times are not interchangeable with the original timing protocol.
- The external estimator-comparison script reported at /tmp/est_cmp.py was absent on this machine. Its results and citation-based claims of finite-sample unbiasedness or optimality are not independently verified and not adopted.
- This repair bundle does not restore deleted round16 publication files. Paper/formula changes remain a separate authorized action.

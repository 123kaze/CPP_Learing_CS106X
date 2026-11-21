# Dataset-cluster uncertainty and system assumptions

Analysis only. Original inclusion/cohorts/grouping retained. New uncertainty resamples whole datasets, not748dependent cases. Only8dataset clusters: intervals are sensitivity estimates, not a population-wide or equivalence guarantee.

| Cache | Counts | Original21-cluster effect | Dataset-cluster95%CI | Historical cluster p(two-sided) | Equal-dataset effect (sensitivity) |
|---|---|---:|---|---:|---:|
| index | old_ra_fp | 0.975135 | [0.947326,1.001193] | 0.095799 | 0.965786 |
| index | repaired_ra_fp | 0.975084 | [0.947281,1.001171] | 0.095799 | 0.965753 |
| fp64 | old_ra_fp | 0.965562 | [0.939300,0.986164] | 0.064650 | 0.949129 |
| fp64 | repaired_ra_fp | 0.965566 | [0.939288,0.986177] | 0.064650 | 0.949131 |

## Dataset effects (descriptive, repaired counts)

| Cache | Dataset | Workload groups | Geometric paired RA/Replay |
|---|---|---:|---:|
| index | caida | 5 | 0.941902 |
| index | caida_flow | 1 | 0.983611 |
| index | cod | 4 | 0.973823 |
| index | mawi2020_flow | 1 | 0.976347 |
| index | mawi2021_flow | 1 | 0.898925 |
| index | mawi2022_flow | 1 | 0.934246 |
| index | shalla | 4 | 0.995295 |
| index | url | 4 | 1.027730 |
| fp64 | caida | 5 | 0.951816 |
| fp64 | caida_flow | 1 | 0.970106 |
| fp64 | cod | 4 | 0.967972 |
| fp64 | mawi2020_flow | 1 | 0.905842 |
| fp64 | mawi2021_flow | 1 | 0.890531 |
| fp64 | mawi2022_flow | 1 | 0.920456 |
| fp64 | shalla | 4 | 0.979652 |
| fp64 | url | 4 | 1.012973 |

## Interpretation

- No repeated regrouping to obtain p<.05. The historical21-cluster test is reproduced, not promoted to a dataset-independent test. The new primary interval keeps its original effect weighting but clusters resampling at dataset level.
- “Similar observed FP counts at lower selection cost” is supported as a descriptive engineering tradeoff; “statistically equivalent”, “universally better”, and “significantly lower FP” do not follow.
- Selection efficiency is a separate contribution: round15 measures learning-length scaling to100M with fixed candidate grid. It is not an asymptotic class separation at fixed candidate count. Old statistic-only timing cannot be transferred to the replay-based zero guard.

## Memory and guarantees

resources.csv contains60historical actual selected configurations, including complete filter byte totals and the external member-index cost. All60 totals are checked. The selected representative cases are unaffected by the GT gap repair. They are not new deployment executions.

| Component | Verified-prefix index supplied by backend | Index-free fp64 |
|---|---|---|
| Executable model, BF bits, thresholds/navigation, array headers | Inside filter budget | Inside filter budget |
| Packed CLOCK array including header and empty slots | Inside filter budget | Inside filter budget |
| Sorted member-hash verification index | Backend8*n bytes + owning-array header | Not required for cache verification |
| Backend records/exact keys | Backend, not measured as zero | Backend, not measured as zero |
| Training, scoring, learning counters, candidate scratch | Construction/selection workspace, not deployed-filter budget | Same distinction |

- If the backend does NOT already provide the index, index construction, storage and safe-prefix search are extra work; the verified-prefix design is not automatically native to RocksDB/LSM backends.
- Prefix safety requires definitive negative feedback, a complete static member-hash index and bypass when no safe prefix fits. Member/model/router updates require rebuild/invalidation; checking today’s members is not a dynamic-set proof.
- fp64 has probabilistic false negatives: under ideal non-adversarial hashing, at most min(1,S/2^64) per member query for S resident entries. This is not a universal lifetime, adversarial, or fixed2.4e-15 guarantee. Collision injection confirms an fp64 rejection while the safe-prefix format bypasses the same hash alias.

## Zero-tree is already experimentally covered

- Revalidated round17 predictive variant and round20 exact-learning guard. Guard:192cases,112zero-tree choices,0tail regressions versus BF+Cache,26versus repaired RA6.
- All32TCP-only cases choose BF; all80strong-model controls keep RA6. These are outcomes of the frozen learning rule, not guarantees on future traffic. All80fresh controls choose BF, changing the original no-repeat/Gama reduction.
- Predictive RA6-Z is cheaper but does not always select BF on weak TCP and retains losses; ZGate pays for13BF candidates plus a learned-finalist learning replay. Neither silently replaces original RA6.
- Cancelled round21 stays cancelled;735/2880partial timings do not constitute a completed cost comparison.

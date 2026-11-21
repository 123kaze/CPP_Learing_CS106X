# GT normalization ablation — completed v2

30prespecified case keys ×2cache formats ×3estimators=180records. GT19controls reproduce all60archived same-format FP counts. Both normalized estimators satisfy total effective mass1, but are not SGT or claimed unbiased estimators. Original L,N1,andcounts retain their meanings.

Raw GT19total mass range in this matrix:[1,1.03777633474]. Stage1 and bucket refinement both use the new unseen mass. All32normalized no-repeat controls retain the GT19structure byte for byte and its FP count; this is not a claim about unmodified RA6’s universal equivalence to Gama.

| Cache | Variant | Cohort | Cases | Win/tie/loss vsGT19 | Median paired ratio | Config changes | Payload changes | Rank-changed cases | Top5-changed cases |
|---|---|---|---:|---|---:|---:|---:|---:|---:|
| index | SeenNormalize | all | 30 | 3/22/5 | 1.000000 | 3 | 8 | 5 | 0 |
| index | SeenNormalize | GT-gap affected | 14 | 0/14/0 | 1.000000 | 0 | 0 | 0 | 0 |
| index | SeenNormalize | real_trace | 4 | 1/0/3 | 1.017060 | 1 | 4 | 1 | 0 |
| index | SeenNormalize | TCP_only | 4 | 2/0/2 | 1.000657 | 2 | 4 | 4 | 0 |
| index | SeenNormalize | no_repeat | 8 | 0/8/0 | 1.000000 | 0 | 0 | 0 | 0 |
| index | TotalNormalize | all | 30 | 4/24/2 | 1.000000 | 1 | 6 | 1 | 0 |
| index | TotalNormalize | GT-gap affected | 14 | 0/14/0 | 1.000000 | 0 | 0 | 0 | 0 |
| index | TotalNormalize | real_trace | 4 | 1/2/1 | 1.000000 | 0 | 2 | 0 | 0 |
| index | TotalNormalize | TCP_only | 4 | 3/0/1 | 0.997645 | 1 | 4 | 1 | 0 |
| index | TotalNormalize | no_repeat | 8 | 0/8/0 | 1.000000 | 0 | 0 | 0 | 0 |
| fp64 | SeenNormalize | all | 30 | 2/23/5 | 1.000000 | 3 | 7 | 5 | 0 |
| fp64 | SeenNormalize | GT-gap affected | 14 | 0/14/0 | 1.000000 | 0 | 0 | 0 | 0 |
| fp64 | SeenNormalize | real_trace | 4 | 1/1/2 | 1.019882 | 1 | 3 | 1 | 0 |
| fp64 | SeenNormalize | TCP_only | 4 | 1/0/3 | 1.006997 | 2 | 4 | 4 | 0 |
| fp64 | SeenNormalize | no_repeat | 8 | 0/8/0 | 1.000000 | 0 | 0 | 0 | 0 |
| fp64 | TotalNormalize | all | 30 | 1/25/4 | 1.000000 | 1 | 5 | 2 | 0 |
| fp64 | TotalNormalize | GT-gap affected | 14 | 0/14/0 | 1.000000 | 0 | 0 | 0 | 0 |
| fp64 | TotalNormalize | real_trace | 4 | 0/2/2 | 1.005426 | 0 | 2 | 0 | 0 |
| fp64 | TotalNormalize | TCP_only | 4 | 1/1/2 | 1.002676 | 1 | 3 | 2 | 0 |
| fp64 | TotalNormalize | no_repeat | 8 | 0/8/0 | 1.000000 | 0 | 0 | 0 | 0 |

## Scope and timing

- All cases and losses retained, including zeroFP; ratios use+1smoothing. Cases share data/models and are not independent statistical samples. No post-hoc selection of a winning estimator or change to the main algorithm.
- In this matrix no top5set changed, although some within-grid ranks, final configurations and BF payloads changed. Enforcing mass1 does not guarantee lower held-out FP. The ablation concerns this fixed matrix, not all1146main cases.
- Raw masses here are all at least1. The14repaired gap cases and8no-repeat controls remain unchanged; the8real/TCP controls carry the observed effects. Overall median1 is dominated by invariant controls and must not be interpreted as showing normalization is universally irrelevant. Real under-mass cases are not covered by this matrix.
- V1stopped with129/180saved records because normalization had no separate component timer. Its process walltime included the cost, but the promised breakdown was incomplete. V2only adds timers; all129overlapping non-timing records (including candidate tables and payloads) are exactly unchanged.
- Counting, normalization (including rate hashes), selection, ranking serialization, payload checks and tail/member checks are separated in rows.csv. Tail_and_member_check_s includes the final all-member cache validation, not just query replay. Models/scores are preloaded; no end-to-end training or speedup claim is made.
- Runtime bindings are restored after each arm and on exceptions; frozen source hashes checked. The control leaves original population/bucket functions intact. This is a post-freeze new-variant diagnostic, not new MAWI24holdout evidence.
- fp64finite member checks are0but its guarantee remains probabilistic under ideal hashing; normalization does not eliminate fingerprint-collision FN risk.
- No manuscript edit is performed. Evidence and interpretation remain in the experiment/MD.

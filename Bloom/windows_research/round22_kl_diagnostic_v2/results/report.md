# KL / Dirichlet shrinkage / zero-tree: actual-data diagnostic

**This is the restricted KL-EB22-static13 diagnostic, not a full cache-aware EB-RA6 implementation.** Four predefined static learned prefixes (1/16/48/96 where feasible) compete against all 13 BF/cache fractions using predicted objectives. No confidence-bound guarantee is implemented. Exact learning replay is a separately labeled baseline, not part of heuristic selection.

| Dataset | Workload | Chosen trees | Cache fraction | Heuristic FP | RA6-GT19 FP | BF+learning-replay FP |
|---|---|---:|---:|---:|---:|---:|
| url | zipf1.0-全部 | 48 | 0.0 | 3,999 | 159 | 273,002 |
| url | 每key一次 | 48 | 0.0 | 135 | 177 | 24,282 |
| url | 全新对抗 | 48 | 0.0 | 2,915 | 4 | 3,524 |
| caida | zipf1.0-全部 | 96 | 0.0 | 84,578 | 29,793 | 1,757,535 |
| caida | 每key一次 | 96 | 0.0 | 61,877 | 52,445 | 1,907,649 |
| caida | 全新对抗 | 48 | 0.0 | 36,904 | 23,320 | 16,225 |
| shalla | zipf1.0-全部 | 48 | 0.0 | 344,212 | 61,474 | 503,973 |
| shalla | 每key一次 | 48 | 0.0 | 33,412 | 33,440 | 147,946 |
| shalla | 全新对抗 | 48 | 0.0 | 27,087 | 15,265 | 9,348 |
| caida_tcp_flow | 真实轨迹 | 0 | 0.2 | 50,203 | 55,050 | 50,568 |
| mawi2020_tcp_flow | 真实轨迹 | 0 | 0.05 | 67,211 | 68,394 | 67,267 |
| mawi2021_tcp_flow | 真实轨迹 | 0 | 0.1 | 40,014 | 41,727 | 40,014 |
| mawi2022_tcp_flow | 真实轨迹 | 0 | 0.1 | 55,735 | 58,339 | 55,735 |

## Main observations

- Versus RA6-GT19: 6 wins / 0 ties / 7 losses; median per-case +1-smoothed FP ratio 1.179842.
- Versus BF13-ExactLearning: 9 wins / 2 ties / 2 losses; median per-case +1-smoothed FP ratio 0.827234.
- Versus BF13-Predict-GT19: 7 wins / 4 ties / 2 losses; median per-case +1-smoothed FP ratio 0.827234.
- Zero trees selected in 4/13 cases (the four TCP-only settings).
- Among141 actual static candidates, the unclipped A identity is applicable in only 35; B's two-interior-solution condition holds in 27. There are 1 raw-KL-versus-capped gate reversals within the stored conditional model.
- Holding tree count and cache=0 fixed, EB versus GT19-h has 24 lower, 0 equal and 23 higher actual FP counts across47 pairs. Partition/allocation may change between the pair; this is a shrinkage-pipeline comparison, not a pure distribution estimate error.
- All original RA6 and ordinary BF/BF-replay reference FP counts and stream hashes match the archived round13 records. Old/new GT statistics are identical on this matrix; reused RA6-GT19 results are explicitly labeled, not fabricated as fresh independent timings.
- The learned search has no cache candidates and no160/200-tree prefixes. Therefore its losses on repeated negatives cannot establish that KL theory or a complete EB-RA6 cache-aware selector fails. Conversely, success at t=0 does not establish the proposed full no-replay algorithm or future non-regression.
- CAIDA/Shalla fresh-adversarial cases remain worse than BF and RA6. Even after capped optimization, predicted selected costs are far below actual tail FP. Fitting singleton histograms is not sufficient evidence of unseen-tail predictability. No parameter is retuned after these observations.

## Theory scatter inputs and what they mean

- A scatter compares the capped fixed-T proxy ratio to same-W ideal plain BF with the actual deployed static-filter/plain-BF FP ratio. Differences can include miss-mass estimation, model mismatch, DP smoothing/merging, integer hash counts and ideal BF error—not just clipping. Pure BF with cache is NOT used as the denominator for this T=0 comparison.
- B scatter compares the AM/GM expression with the independently recomputed capped continuous loss on the SAME partition, budget and M. It is a mathematical-model check, NOT a pair of separately deployed q/r filter measurements. In the joint interior region the identity holds; outside it the expression need not equal the capped loss.
- All plotted point-level data are preserved in static_checks.csv; common models/streams make points correlated. No claim of significance or of new information-theoretic novelty is made.
- Real final5-region counts are used, not the optimistic1000-microbin KL. Physical model/metadata/array overhead and available/logical bits are exported. Cached references are labeled with nonshared candidate-dependent T and are not treated as fixed-T identities.

## Timing and reproducibility boundaries

- This is one diagnostic pass, not repeated fair algorithm timing. Per-phase seconds include EB fitting, proxy diagnostics, builds and reference work. selection_pipeline_envelope_s includes extra diagnostics/reference selection and is NOT a standalone selector cost or new speedup result.
- Test tails are accessed after alpha fitting and predictive selection. Posthoc true-tail A/B fields are diagnostic only; no tail controls alpha, candidate ranking or t=0 decisions. Actual FP counts use frozen static flags/cache simulation, not new end-to-end database timing.
- URL/CAIDA/Shalla with three workloads and four TCP-only second budgets:13 non-holdout, indexed-cache, seed0 settings. The matrix is small and prespecified; stronger claims need further independent validation. No entire192-case or fp64 replication is claimed.
- The all-singleton EB input is not forced back to h and did not yield alpha=infinity in these fits. Original RA6 no-repeat reduction does not transfer to this heuristic. EB is a grid-refined working model; no global-MLE guarantee or bootstrap interval is claimed.
- Initial v1 smoke failed at JSON serialization of a NumPy boolean; v2 only converts supported scalar types while still rejecting nonfinite values. Math, worker, candidate matrix and parameters are byte-identical. Failed logs remain separate and no performance result from v1 is used.
- The cancelled shared-replay campaign was not restarted. No paper or frozen experimental source file was edited.

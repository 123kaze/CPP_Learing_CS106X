# Proposal A: fixed LightGBM, only negative training weights change

Three datasets, three weighting arms, six tree prefixes, cache fractions0/10%. One fixed model/workload seed. All108 planned configurations are retained, including12 that cannot fit. TrafficGT is a query-mass control; EscapeGT transfers a fixed reference's cache-residual proxy through32 score bins, not oracle future key-level misses.

## url: 128KiB

Weighted-arm reference acquisition: 0.662s (reference training + scoring/build/mapping).

| Trees | Cache fraction | Uniform FP | TrafficGT FP | EscapeGT FP | Uniform score ns | Traffic score ns | Escape score ns |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.0 | 61306 | 23836 | 61306 | 108.3 | 86.2 | 85.3 |
| 4 | 0.0 | 10123 | 17620 | 11104 | 176.0 | 101.0 | 165.8 |
| 8 | 0.0 | 2985 | 4187 | 4022 | 165.3 | 140.9 | 252.8 |
| 16 | 0.0 | 2430 | 2839 | 12151 | 306.0 | 255.4 | 325.2 |
| 48 | 0.0 | 1415 | 1311 | 1094 | 774.8 | 805.9 | 774.5 |
| 160 | 0.0 | 59522 | 57274 | 68246 | 2654.8 | 2559.6 | 2361.4 |
| 1 | 0.1 | 2328 | 3294 | 2328 | 108.3 | 86.2 | 85.3 |
| 4 | 0.1 | 520 | 1573 | 516 | 176.0 | 101.0 | 165.8 |
| 8 | 0.1 | 415 | 471 | 435 | 165.3 | 140.9 | 252.8 |
| 16 | 0.1 | 289 | 475 | 292 | 306.0 | 255.4 | 325.2 |
| 48 | 0.1 | 262 | 233 | 259 | 774.8 | 805.9 | 774.5 |
| 160 | 0.1 | 55753 | 55273 | 54108 | 2654.8 | 2559.6 | 2361.4 |
## caida_tcp_flow: 32KiB

Weighted-arm reference acquisition: 0.185s (reference training + scoring/build/mapping).

| Trees | Cache fraction | Uniform FP | TrafficGT FP | EscapeGT FP | Uniform score ns | Traffic score ns | Escape score ns |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.0 | 172405 | 169499 | 182734 | 57.0 | 46.0 | 67.0 |
| 4 | 0.0 | 211523 | 171581 | 184971 | 104.4 | 82.7 | 117.2 |
| 8 | 0.0 | 212635 | 196522 | 196350 | 194.3 | 119.1 | 186.0 |
| 16 | 0.0 | 254179 | 259313 | 249493 | 249.6 | 208.1 | 249.5 |
| 48 | 0.0 | infeasible | infeasible | infeasible | — | — | — |
| 160 | 0.0 | infeasible | infeasible | infeasible | — | — | — |
| 1 | 0.1 | 57300 | 56753 | 55753 | 57.0 | 46.0 | 67.0 |
| 4 | 0.1 | 60768 | 59439 | 59668 | 104.4 | 82.7 | 117.2 |
| 8 | 0.1 | 66990 | 66051 | 65905 | 194.3 | 119.1 | 186.0 |
| 16 | 0.1 | 80470 | 80762 | 80396 | 249.6 | 208.1 | 249.5 |
| 48 | 0.1 | infeasible | infeasible | infeasible | — | — | — |
| 160 | 0.1 | infeasible | infeasible | infeasible | — | — | — |
## caida: 256KiB

Weighted-arm reference acquisition: 4.290s (reference training + scoring/build/mapping).

| Trees | Cache fraction | Uniform FP | TrafficGT FP | EscapeGT FP | Uniform score ns | Traffic score ns | Escape score ns |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.0 | 367523 | 416747 | 350094 | 49.9 | 77.7 | 113.0 |
| 4 | 0.0 | 330356 | 348431 | 313886 | 119.3 | 137.4 | 161.7 |
| 8 | 0.0 | 272950 | 283726 | 289386 | 134.0 | 122.2 | 201.9 |
| 16 | 0.0 | 218790 | 210282 | 202090 | 288.6 | 213.5 | 188.7 |
| 48 | 0.0 | 140708 | 144370 | 125112 | 789.2 | 655.1 | 608.2 |
| 160 | 0.0 | 75194 | 83514 | 87868 | 2929.0 | 3162.0 | 2902.7 |
| 1 | 0.1 | 199536 | 194678 | 197682 | 49.9 | 77.7 | 113.0 |
| 4 | 0.1 | 172975 | 187390 | 166696 | 119.3 | 137.4 | 161.7 |
| 8 | 0.1 | 135112 | 131483 | 145066 | 134.0 | 122.2 | 201.9 |
| 16 | 0.1 | 102099 | 106955 | 104685 | 288.6 | 213.5 | 188.7 |
| 48 | 0.1 | 52134 | 55476 | 52795 | 789.2 | 655.1 | 608.2 |
| 160 | 0.1 | 27844 | 29316 | 28364 | 2929.0 | 3162.0 | 2902.7 |

## Boundaries

- EscapeGT versus Uniform has 17 wins, 2 ties and 13 losses across32 feasible matched configurations. This is mixed exploratory evidence, not a stable general advantage.
- No demonstration that a few weighted trees replace160 unweighted trees on the intended full-budget tradeoff. Tree-prefix results and infeasibility are preserved rather than selecting a favorable winner after testing.
- All arms use identical LightGBM settings and training-key identities. Negative weights are mean-normalized to1, positives stay1. A fixed reference16-tree/10%-cache predictor transfers coarse-bin learning mass to disjoint training negatives; this is not true per-training-key future m_x or joint model/cache training.
- TrafficGT separates adaptation to query distribution from cache-specific absorption. Reference assumptions can become inaccurate when final model/cache configuration changes; weights are not recomputed to fix observed failures.
- Three native-loop timing repetitions use known labels for simulated feedback, not a real database. Input hashes and features are prepared; standalone scoring and full model/BF/cache costs are distinct. There is only one model/workload seed; no significance or paired cross-campaign speedup claim.
- Weighted arms incur extra reference training/scoring/mapping cost. Full tree model is trained once per arm, prefixes reused. The application does not automatically choose a prefix from test outcomes.
- All feasible member/pool-native checks passed. Old frozen methods, cancelled experiments, dependency environments and paper files remain unchanged.

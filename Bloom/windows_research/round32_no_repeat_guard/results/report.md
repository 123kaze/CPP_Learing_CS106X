# RA6-NR32: explicit no-repeat Gama dispatch

**Complete:**140original no-repeat cases reproduce both original Gama and RA6 tailFP, and independently rebuilt Gama deployment arrays match byte for byte during execution. Four repeated controls delegate to original RA6 and reproduce its payload/FP.

This is a new post-hoc variant, not a repair claimed to have existed before the MAWI24freeze. No original algorithm, main table, cancelled experiment or paper was edited by this round.

## Conditional implementation guarantee

For valid finite inputs with a nonempty learning period, a deterministic shared builder and at least one feasible no-cache candidate:

1. The guard checks raw counts:the number of keys equalsL and every count is1. It does not infer no-repeat from approximate rate mass.
2. In that branch it calls frozen E5.candidates with exactly the same tree grid and frac=0. The zero-cache candidates are the same subset used by E5.gama in the full grid; no cache candidate build mutates their inputs.
3. It selects by that same E5.gama function, including its (estimatedFPR,treecount) tie-breaking, and returns the selected already-built candidate. Therefore it cannot substitute RA’s differently masked score or top5 ranking.
4. For repeated input it passes the same setup,scores,learning summary,budget,H andtopk to frozen ra6.select6 and returns that object. Only reporting metadata changes.

Thus exact selection equivalence is by shared code path for NR32. It is NOT a proof of universal equivalence for unmodified RA6, whose scoring mismatch remains documented. The bounded18-case search in round30 found no counterexample; this round does not relabel that negative search as a counterexample.

## Executed regression

| Dataset | No-repeat cases | Bit-equal/FP-equal | Median guard select+build(s) | Repeated control FP |
|---|---:|---:|---:|---:|
| cod | 30 | 30 | 1.1240 | 45 |
| url | 30 | 30 | 0.3042 | 159 |
| caida | 40 | 40 | 2.6373 | 29793 |
| shalla | 40 | 40 | 1.4635 | 61474 |

## Verification and limits

- Execution compares actual contiguous uint8 views with numpy.array_equal, plus shapes/dtypes and configuration; hashes are retained for archive checking, not substituted for the live byte comparison. PackedBF is rebuilt and all members checked; all query-pool flags match.
- CSV timing separates counting,selection/build,payload checking andtail evaluation. Models/scores are preloaded, not trained in this timer. No new speedup claim is inferred from one sequential timing percase.
- Fresh-adversarial seedlabels can denote the same deterministic stream. Cases share models and data;140is not140independent samples. No MAWI24result was regenerated or relabeled as a new holdout.
- NR32 does not add zero trees and does not guarantee futureFP optimality, BF+Cache non-regression or lower latency. RA6-ZGate remains a distinct replay-cost variant.
- Empty learning inputs are explicitly rejected. This is not an assertion that the old code had a defined result forL=0.
- Manuscript advice: either state candidate-wise weight reduction/empirical equality for the old implementation, or explicitly label the new dispatch variant and its post-freeze date when claiming a universal same-Gama selection guarantee.

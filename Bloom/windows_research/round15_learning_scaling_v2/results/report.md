# Learning-period scaling: 1M to 100M queries

CAIDA,256KiB,Zipf1.0,180 feasible candidates (14×13 nominal grid). Each point contains three fresh single-threaded runs; no pilot observations or extrapolated times are plotted. Both selection timers include learning-dependent counting; Replay additionally includes local-key mapping. Trained models, scores and length-independent segment arrays are prepared before either timer.

| Learning queries | Distinct keys | Pool seen | RA-PLBF/RA6 s | Replay s | Paired speedup | Paired time gap s |
|---|---:|---:|---:|---:|---:|---:|
| 1,000,000 | 307,691 | 5.3% | 3.049 | 6.867 | 2.24× | 3.818 |
| 2,000,000 | 530,465 | 9.1% | 3.321 | 10.825 | 3.26× | 7.504 |
| 5,000,000 | 1,048,225 | 18.0% | 3.900 | 23.855 | 5.96× | 19.675 |
| 10,000,000 | 1,683,202 | 28.8% | 4.394 | 44.816 | 10.35× | 40.285 |
| 20,000,000 | 2,570,036 | 44.0% | 5.541 | 105.841 | 19.18× | 100.348 |
| 50,000,000 | 4,026,219 | 69.0% | 7.628 | 275.429 | 36.95× | 267.976 |
| 100,000,000 | 5,043,212 | 86.4% | 9.747 | 479.965 | 49.24× | 470.218 |

## Phase medians (do not add medians to obtain the total median)

| L | RA count s | RA prediction/DP s | RA top-5 build/refine s | Replay count s | Replay mapping s | Replay builds s | Replay ordered scans s | Replay scan visits / L |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000,000 | 0.024 | 2.907 | 0.121 | 0.020 | 0.016 | 4.164 | 2.586 | 65.952 |
| 2,000,000 | 0.046 | 3.123 | 0.152 | 0.041 | 0.029 | 5.025 | 5.674 | 64.158 |
| 5,000,000 | 0.111 | 3.579 | 0.214 | 0.102 | 0.084 | 6.723 | 16.806 | 63.900 |
| 10,000,000 | 0.208 | 3.897 | 0.290 | 0.203 | 0.178 | 8.566 | 35.931 | 64.695 |
| 20,000,000 | 0.422 | 4.675 | 0.395 | 0.400 | 0.527 | 11.789 | 93.072 | 65.262 |
| 50,000,000 | 1.039 | 6.006 | 0.561 | 1.006 | 1.579 | 16.934 | 255.973 | 65.746 |
| 100,000,000 | 1.902 | 7.171 | 0.674 | 1.831 | 3.112 | 19.897 | 455.331 | 65.912 |

## What this establishes—and what it does not

- Over the 100× increase in L, RA6's total selection median grows 3.20× and Replay's 69.90×. The endpoint paired-speedup medians are 2.24× and 49.24×. Monotonically increasing across all seven medians: **yes**.
- An increasing seconds gap is not by itself a different asymptotic class. These are measurements for one finite pool, workload, budget and fixed candidate set, not a proof as L approaches infinity.
- RA6 counts once per selection, builds populations per tree prefix, scores every candidate and builds five candidates. It avoids repeating ordered learning traces for each candidate; it is not independent of L, distinct-key count D, or candidate count C.
- The frozen counter uses sort-based np.unique with return_counts, not a proved O(L) streaming counter. Both timers include their counting. Replay also maps L indices; the table separately exposes mapping and actual candidate scan costs.
- Replay retains exact incumbent early stopping and zero-cache weighted counting. Its relevant scan term is the sum of actual candidate visits (bounded above by 166L here), not an assumed 180L. No scans were disabled or inflated to produce a favorable ratio.
- Fixed-pool coverage and distinct keys are reported because repetition increases as the pool saturates. Per-tree population work and top-five refinement still depend on these statistics. Dependence on candidate count cannot be identified by this fixed-C experiment alone.
- H=3L is the predicted deployment horizon, but no 300M-query evaluation tail was allocated. Choice validity, all-member acceptance and selected-BF equality are checked outside timing. Learning FP counts do not establish held-out prediction quality.
- This is selection cost with cached scores, not full training-to-ready time or a comparison with the authors' original Gama implementation. Early rounds and paper files are unchanged.
- Min–max intervals describe three timing repetitions of the same nested stream, not independent workload confidence intervals. No unfavorable repeat is dropped. Whole-process RSS includes shared model setup and post-timing checks.
- The initial launcher generated the stream but failed on an unavailable optional threadpoolctl import before a selection measurement. v2 reuses the identical stream and removes that instrumentation dependency. Failed logs and frozen sources remain in the previous directory.

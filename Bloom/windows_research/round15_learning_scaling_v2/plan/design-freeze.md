# Round 15: learning-period scaling, 1M–100M (2026-11-16)

## Question and frozen scope

Does RA-PLBF/RA6's avoidance of per-candidate ordered replay produce an increasing practical selection-time advantage as the learning period grows? Do not presuppose a favorable curve or label a fixed-candidate experiment an asymptotic-complexity proof.

- CAIDA synthetic, 256 KiB, Zipf exponent 1.0 over the full fixed negative pool; same frozen model, scores and train/validation/pool split as round-6 E5.
- L = 1, 2, 5, 10, 20, 50, 100 million learning queries. Three fresh processes per method per length; two methods = 42 formal workers. Repetitions are timings of identical data, not new independent workload seeds.
- The same 14 tree prefixes × 13 cache fractions, filtered only by the original physical feasibility check. Preflight confirms180 feasible candidates out of182 nominal combinations: (160 trees,0.6 cache fraction) and (200 trees,0.6) do not fit. Candidate-grid digest must be identical at every length and for both methods.
- One new nested stream: a fixed permutation (seed15001) of pool IDs, Zipf inverse-CDF draws (seed15002), generated in 1M-row chunks into an int64 mmap. Every L is a prefix of this same 100M stream. This is a new fixed stream, not claimed bit-identical to old E5, whose mapping depends on requested stream length.
- RA6 retains the old protocol's predicted horizon H=3L (25/75), but no 300M-query evaluation tail is materialized. This is a selection-cost experiment; no new held-out FP-quality claim is made. Selected Replay learning FP is checked separately, not reported as held-out quality.
- Separate 100K-query pilot (two processes), excluded from the chart. Pilot must reproduce canonical frozen RA6 selection and full-pool flags, and Replay's winner must match a no-cutoff evaluation of all candidates. Both methods' selected local flags must match a frozen full-pool BF build, which checks all members and the byte budget.

## Fair timing boundary

Common trained model/scores and L-independent tree-segment inputs are prepared before timing for both methods. No model fitting, score precomputation, loading, stream generation, JIT warmup, input hashing, chart generation or post-selection verification enters the selection curve. This is not train-to-ready or original-Gama system timing.

Primary y = time from resident raw learning-index array to selected configuration, including **all learning-dependent preprocessing**:

- RA6: frozen `ra4.summarize` (counts and Good–Turing rates), per-tree populations, all-candidate prediction/DP, top-five DP/BF insertion and bucket refinement.
- Replay: distinct-key counts, conversion to a local-key sequence, local hash/safe arrays, every candidate's DP/BF insertion/static queries, ordered cache replay and winner selection.

Unlike old E5, Replay's key compression is now inside the timer. Its counts come directly from `np.unique(return_counts=True)` rather than repeating a bincount after mapping. Mapping is chunked to bound temporary allocation, with identical int64 local indices.

Both methods import round-6 E5's local-query DP/BF helper; no rebuilding/querying all pool keys inside one method's timed path and only observed keys inside the other. The common model/segments are fixed; learning-key BF flags are not shared between candidates or methods. Final independent full-pool/member verification is outside both timers.

Replay retains exact incumbent early stopping and the no-cache frequency shortcut. Record candidate count, built count, cache-bearing count, number cut off, and actual processed query visits per candidate. Never disable these optimizations to manufacture separation. RA6 records zero per-candidate ordered replay visits, but its initial counting still reads the stream.

Record individual and aggregate phase times, L, distinct-key count D, predicted H, selected configuration, learning trace/state bytes, whole-process RSS and source/input digests. RSS includes common model and untimed validation, not deployment memory or pure selection peak.

## Complexity interpretation

Counting is done once per selection, **not once across all different experiments**. Population construction is once per tree prefix, and candidate scoring is still performed for every feasible candidate. RA6 is not independent of L, D, tree count or candidate count.

The frozen summarizer uses `np.unique(..., return_counts=True)`, with sort-based work; do not call the current implementation a proved O(L) streaming counter. Replay also counts once and additionally maps L indices. Model costs for this implementation as:

- RA6: one counting pass implemented via sorting + per-tree distinct-key/population work + candidate DP/modeling + five BF constructions/refinements.
- Replay: one counting/mapping step + all-candidate constructions + sum of the actual ordered query scans, at most O(C_cache × L). Early stopping and zero-cache shortcuts can reduce scans.

With C fixed, an increasing absolute time gap alone is not a different big-O class. Plot and report **paired speedup versus L** as well as seconds; distinguish growth of D from repetition after D approaches the finite pool size. A rising speedup supports measured amortization over this workload/range, not unlimited asymptotic growth. General dependence on candidate count requires a separate axis/study (old E5 provides limited prior evidence, not a new measurement here).

## Execution, reporting and failure policy

One CPU thread, fresh processes, all serial. Method order alternates across length and repetition. Small warmup uses at most4096 unrelated-to-measured-size prefix queries; no prebuilt candidate or summary is reused for the timed selection. No tracemalloc in timing. Limit major arrays through chunked generation/mapping; maximum input payload800MB, no 4L stream.

Failure is propagated; partial/error files are never automatically retried. Memory-pressure termination requires user approval before restarting. Keep every repetition and any unfavorable result. Freeze sources before launch, verify all required caches before running. No frozen-source edits, paper edits, local TeX installation, fabricated measurements or new significance claim.

## Deliverable

One English-labeled figure: learning length on x; inclusive selection seconds on primary panel y, RA-PLBF/RA6 and Replay lines, three-run medians and min–max ranges. A separate same-figure panel shows median paired speedup, never a dual y-axis. Provide PNG/PDF, full CSV/JSON and readable timing-boundary/complexity discussion. A log-x view accommodates100× range; any additional linear-axis rendering is labeled explicitly, not used to change the conclusion.

## v2 instrumentation-only correction

The first version generated the complete stream, then failed at the pilot worker's import of unavailable threadpoolctl. No selection measurement completed. This version removes that optional dependency and records the five single-thread environment settings plus the actual Numba thread count. It reuses the exact generated input and changes no selection, counting, candidate, replay or timing-boundary logic. Old frozen sources and failed logs remain in ../round15_learning_scaling.

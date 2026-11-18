# Round20: explicit zero-tree safeguard by empirical learning replay

## Why another variant

User requested trying t=0 without degradation. Round17 predictive RA6-Z made zero-tree available but could prune the entire family or misrank it; this new method **RA6-ZGate** does not depend on that global shortlist to retain a BF alternative. It changes the selector and its cost, not the fixed BF, cache or learned allocation implementation. Previous rounds remain frozen.

The no-degradation property is stated precisely for the observed LEARNING objective; future-tail effectiveness is tested without any assertion forcing the desired outcome. No test-tail oracle, dataset-specific fallback threshold or post-result retuning.

## Fixed rule before running

1. Use the repaired round19 frequency estimator, then call the frozen RA6 top-five selection to obtain one learned anchor. RA6-ZGate retains this anchor unconditionally.
2. Build all13 zero-tree/cache candidates using round12's exact owning-array physical representation. No model/learned metadata charge.
3. Select the BF family's winner by exact learning replay with the frozen order/tie rule `(fp,estimated_fpr,trees,frac)`, incumbent early stopping and zero-cache frequency shortcut.
4. Replay the single learned anchor on the SAME entire learning window with cold cache, obtaining its exact learning FP. No prediction replaces this count.
5. Pick the smaller learning FP; on equality choose the BF-family winner(t=0). Thus measured learning FP equals `min(FP_learn(BF-replay winner), FP_learn(RA6 anchor))` and cannot exceed either.

The guard sees only learning indices and predicted horizon length H. It accepts no evaluation-tail array or tail score. Tail is evaluated after the selection returns. The learning bound is NOT claimed as a held-out guarantee, independence claim or distribution-free generalization theorem. Selecting pure BF every time would trivially match BF but lose learned benefits; this rule permits either family based on actual learning evidence.

This is no longer a statistics-only selector: it pays for13 BF candidates plus one learned-anchor replay (zero-cache shortcuts/early cuts can reduce scans). Record summary, learned selection/build, pure candidate building, BF replay and anchor replay times including all candidate construction per case. Timings are diagnostic, not a new rigorous scaling comparison; model/scores are prepared caches and JIT may affect early cases. No claim that the prior49.24× speedup applies to this variant.

## Data and comparisons

Reuse round17's ENTIRE192 cache-specific matrix with no cherry-picking:
-32 TCP-only cases:four datasets ×four budgets ×two cache formats.
-80 stronger-model controls:COD1024/URL128/CAIDA256/Shalla1024KiB ×Zipf1.0/full and every-key-once ×seeds0–4 ×two formats.
-80 fresh-adversarial cases:all four original CAIDA budgets and all four Shalla budgets ×seeds0–4 ×two formats. Fresh-stream seed labels do not imply independent traces.

Same frozen first25% learning and last75% cold evaluation; no probe-dependent tails in this matrix. The rate digest must show this matrix is unaffected by the round19 bug fix before claiming reference equality.

Freshly build/evaluate three methods per case:RA6-ZGate, repairedRA6 anchor, BF+ReplayCache (576 live method records). Reproduce round17 anchor/BF configuration, static flags and tail FP/hits, and BF learning count. Old predictive RA6-Z and expandedReplay+Z are read only AFTER selection and labeled historical comparators, not remeasured timing baselines.

When zero-tree is selected, run the full tail through the standalone native BF/CLOCK path and compare with frozen simulation; populated-cache member acceptance and actual owning-array/cache bytes must hold. Indexed member index remains outside budget; fp64 collision limitations remain, despite fixed-input checks. Neither branch is Direct/no-filter, and this FP experiment is not a database latency result or zero training cost during search.

## Safety checks and execution

Eight unit tests pass before freeze: BF/learned/tie decisions, exhaustive small empirical bound, a future-tail counterexample to avoid claiming an invalid guarantee, malformed counts, native zero serialization and comparison to both the frozen early-stopping selector and no-cutoff exhaustive BF learning results.

Separate CAIDA TCP16KiB pilot in each format: all14 guarded candidates are exhaustively replayed without early cutoff, and the final learning objective must match. Pilot excluded from192 formal cases. Then16 serial fresh dataset/cache processes, single-threaded. Completed matching results may be skipped; partial/error results stop without automatic retry; memory termination needs user approval. Full source/input provenance before/after. No old source, paper, dataset or archived result edits. No restored deleted publication content.

## Gama implementation check

In the author's original checkout used in our comparisons, `lgb_url_GamaPLBF_ada.py` scores initial positive-tree models, skips the first tree and searches with `l_bound=2`. Its `best_epoch=0` is an initial sentinel, not a no-model BF branch. The inspected G-LBF Bayesian script searches(1,200). The shared implementation's GAMA_TREES begins at1. This statement is limited to the inspected implementations, not every possible Gama variant or theoretical extension. Upstream source remains a submodule/local adapter, never copied into this new public round.

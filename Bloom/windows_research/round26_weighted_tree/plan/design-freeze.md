# Round26: proposal A — only change LightGBM negative training weights

## Fixed first experiment

User explicitly requested A after clarifying that prior MLP loss and cell-table trials were not this experiment. Same binary LightGBM params across arms:num_leaves31,learning_rate.1,seed1,deterministic=True,force_col_wise=True,num_threads1; same train members/negative identities/features, no member query or test tail used for weights.

URL128KiB, CAIDA256KiB, CAIDA TCP-only32KiB. Synthetic Zipf1.0 over full negative pool,seed0,total10M; real TCP stream original order. First25% learning; last75% cold evaluation. Three weight arms x six prefixes(1,4,8,16,48,160) x two fixed cache fractions(0,.1) =108 candidate configurations, with infeasible ones retained. One fixed workload/model seed is exploratory, not significance evidence. Three native timing repetitions per feasible structure; not three training initializations.

## Reference proxy and disjoint-key transfer

Train a fixed16-tree unweighted reference on the original train split. Build its static validation-weighted PLBF at the same total budget with10% external cache. Reference training/scoring/build cost is charged to weighted arms; uniform control does not need this reference.

Training negatives and learning negatives are disjoint by key. Therefore the experiment does NOT assign oracle m_x to training keys. Instead it transfers learning-only residual quality via32 reference-score rank bins whose boundaries are quantiles of TRAINING negative scores. Mapping assumptions must be explicit.

Use GT19 rates on learning keys. Aggregate member counts, validation-negative h(add-one), learning rate/multiplicity and unseen GT mass into the32 bins. Construct the frozen RA4 Population. Average the reference PLBF's per-microbin continuous FPR within each coarse bin on reserved validation negatives; an empty validation bin conservatively uses epsilon=1. Its fixed cache slots set the capacity.

- Uniform:all negative training weights1.
- TrafficGT:target mass per bin is P.Mg[0], the estimated future negative query mass without cache absorption.
- EscapeGT:target mass per bin is P.misses(reference_epsilon,reference_slots,setassoc=True), the frozen conditional residual-miss proxy BEFORE multiplying by filter FPR.

For either weighted arm, normalize bin mass into a target distribution, mix1e-6 of training-negative bin proportions, divide by training bin proportions, then normalize the negative sample weights to mean1. Positive weights remain1. This preserves total class-weight balance. Unsupported target mass is reported instead of treating unseen training keys as zero weight. No clipping/tuning of high weights after observing results.

The TrafficGT arm distinguishes simple query-distribution adaptation from cache-specific absorption. EscapeGT is a fixed-reference, bin-level proxy, not the true expected future escape count of each training key; it is not recomputed after every training update. Different final cache fractions/trees can have different optimal weights. This is the minimal conditional test, not joint training/cache optimization or proof that one line of weight= solves the full task.

## Same downstream pipeline and evaluation

Each arm freshly trains160 trees; evaluate its prespecified prefixes. Reuse frozen E5 candidate construction, validation-only BF weights, physical accounting, CLOCK and native tree path. No RA6 reweighted candidate search is mixed in, and no best prefix/cache is chosen using test FP. Fixed budgets may make large models infeasible; record rather than silently replace them.

Recompute native arrays for each fitted prefix and clear only in-memory per-model caches. The unweighted160 model's16 prefix must exactly reproduce the fixed unweighted16 reference scores. Each feasible structure checks all-member acceptance and pool-wide native flags equal frozen built BF flags; native mixed-query loops and final member cache-hit checks are retained.

Measure training, weight-reference preparation, scoring, filter building, standalone native tree traversal and native model/BF/CLOCK query cost on fixed100K requests(90% test-negative keys,10% members). Timed loops execute real operations, but known membership supplies simulated feedback; this is NOT a database latency/feedback integration. Input feature extraction and key hashing are precomputed outside these timings. Preserve per-query FPR on the complete evaluation tail, plus static pool FP, model bytes and validation-region KL. KL is descriptive and not an unclipped deployment guarantee.

The whole series includes baselines as data, not a winner-selection procedure. Report failures, infeasible models and cases where weighted training harms FP or runtime. No fixed claim that a few trees will match160 trees; evaluate both honestly. No new dependencies, old frozen edits, paper changes, or new public-main merge. Work remains isolated on experiment/lightweight-scorers.

## Tests and safety

Weight unit tests verify density-ratio transfer, positive finite weights, mean-negative1, unsupported-bin reporting and rejection of zero total mass. Runtime asserts repaired rates are from learning only, negative training IDs disjoint from learning IDs, same parameters across arms, actual native thread counts1 and model/FP consistency. Sources and raw cache/reference inputs hashed before running. Serial jobs only; failure stops without auto-retry. Memory-pressure restart requires approval.

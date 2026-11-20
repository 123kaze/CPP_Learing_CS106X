# Round23: first-stage lightweight scorer replacement

## Branch and scope

User requested a new branch and a first test following docs/轻量模型与缓存感知Bloom过滤器_研究思路.md. Work branch:experiment/lightweight-scorers in the experiment repository. Old RA6 code, publication history and paper are not modified. This is a model-screening experiment, not a claimed new training algorithm.

First isolate model choice: no negative cache, no new Good–Turing/KL/EB rule, no joint residual-cost training and no PCA. User's subsequent feature-cell partition and weighted-training proposal is a separate next-stage exploration, not mixed into this frozen baseline. No more datasets/hyperparameters are added after observing results.

## Data, models and budgets

Prepared URL (18 features) and CAIDA TCP-only (2 address features), original key-hash train/negative-validation/negative-test split. URL budgets64/128KiB; TCP budgets16/32KiB. No data download or raw preprocessing change. Member set is used for BF construction as required, but only member_train|neg_train fits models/preprocessing. Negative validation chooses PLBF segmentation/allocation; test negatives never select features/parameters. Classification AUC uses held-out members plus test negatives and is diagnostic only.

Models, all fixed before run:
- Pure BF: no model or learned metadata, exact round12 owning buffer and integer-k formula.
- LR: standardized features, binary logistic loss plus L2=1e-4.
- GaussianNB: train-derived standardization, two class means/variances and prior; variance floor1e-6 in standardized space.
- Additive16:16 marginal quantile bins per original feature, learned additive logit tables plus bias, logistic loss/L2. All features used; no interactions or claimed sparsity. Tied quantile edges retained with consistent right-inclusive search.
- MLP8: one ReLU hidden layer of8, logistic output, L2 on matrices. Train-derived standardization; deterministic seed1 initialization.
- Tree1/Tree16: independent LightGBM binary models,31 leaves,learning_rate.1,seed1,one thread; unchanged tree extraction helper. No full200-tree capacity search.

LR/Additive/MLP use scipy L-BFGS-B with100 maximum iterations and fixed tolerances. Optimization may stop without convergence; retain optimizer status/message/iteration count and never relaunch or increase the budget to improve outcomes. These are fixed first-test settings, not equally tuned optimal representatives of each model family. GaussianNB is a generative closed-form contrast, not the same loss.

All deployed scoring parameters float64; tree node-index arrays int16. No quantization experiment. All raw features finite and used unchanged from the prepared caches. Existing address float32 representation is retained; no assertion that this is the best address encoding.

## Common downstream filter and exact physical accounting

Every learned model feeds the frozen FastPLBF DP(N=1000,k=5), region-bit allocation and frozen hash/BF build/query routines with validation weights. This is static Gama-style per-scorer partitioning, not RA6 selection.

The new generic deployment stores actual model owning arrays(including mean/std or bin edges), a24B layout/type header plus its ndarray header, four score-probability thresholds, region kinds/offsets/bit counts/hash counts, and packed BF bits. Count sys.getsizeof of every required owning array, not theoretical model coefficients only. The generic dispatcher uses shared empty placeholder arrays for inactive model families; those are harness objects, not serialized per-filter state. Python container/interpreter/JIT, request features and prehashed keys are explicitly outside this representation; it is not total-process accounting.

Compute remaining BF bit budget only AFTER model/preprocessing/navigation/array-header costs. Assert all members accepted, deployment<=budget, frozen-region flags equal real native model+BF queries for every input key, and model/layout buffer reload byte-identical outcomes. PureBF retains its stronger exact one-array representation without invented learned overhead. If a fixed model cannot fit, the worker fails visibly; do not silently pretend that configuration is zero-cost.

The generic native scorer is separately checked against the reference fitted model on10000 fixed rows, and reloaded models must reproduce all native scores exactly. Synthetic tests check gradients for all optimized models, tied-bin boundaries, constant features, native equivalence and BF budget/round-trip correctness.

## Measurements

Two datasets x3 fresh processes. Each process trains all6 learned model configurations from scratch with seed1; order rotated by repetition. Each model is evaluated at2 budgets plus pureBF:84 filter records and36 model trainings.

Report model fitting time(includes preprocessing/training data conversion), model scoring preparation, filter-build time, train convergence/status, actual model bytes/payload, BF bits and all static test-negative FP counts. AUC is supplementary, not the optimization target. All smaller/larger model outcomes retained.

Use a fixed100K-request microbenchmark with90K uniformly sampled test negatives and10K members(seed2301), same sequence for all methods. Each key undergoes actual independent native scoring and, for filter timing, BF bit probes. Three timings after warmup per fitted instance. Scalar scoring logic lives INSIDE a Numba native loop; Python call overhead is batch-amortized. These numbers are not independent Python API single-query latency, p99, cache-aware workload timing or database throughput. Key hashing and raw feature extraction are not in these timers; standardization/binning IS in the scorer. PureBF uses the same precomputed hashes and request order. No precomputed model scores or FP flags replace timed queries.

Thread environment is set BEFORE NumPy import. Assert actual OpenBLAS=1 and Numba=1 in every worker. Run all6 jobs serially; preserve failures/no automatic retry, ask before restarting a memory-pressure termination. JIT warmup and verification outside timed intervals. Model inputs and sources hashed before launch, frozen sources checked after completion. No cancelled shared-replay or deleted published round16 experiment is restarted or restored.

## Interpretation

This can identify promising byte/FP/native-inference tradeoffs on two fixed datasets, not a universal best classifier or new publication claim. A positive outcome would motivate same-model training-objective ablations or cache integration later. No promised latency win, no new probability/calibration theorem, no use of held-out data to select hyperparameters. The complete stopped-nonconverged models and measured regressions must be disclosed.

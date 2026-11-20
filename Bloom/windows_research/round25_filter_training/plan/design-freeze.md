# Round25: same MLP8, only the training objective changes

## Question and scope

Test whether downstream filter-aware training can improve actual static PLBF effectiveness at the SAME model size. This is a new trial on branch experiment/lightweight-scorers, not an update to frozen RA6. User approved testing this narrow follow-on. No negative cache, KL gate, Dirichlet shrinkage, 8-bit quantization, new features, lookup-router architecture or unknown-label acquisition is mixed in.

Same prepared URL64/128KiB and CAIDA TCP16/32KiB; same train/validation/test as round23. Same float64 scalar-score MLP with8 ReLU units and identical parameter storage/normalization. Actual model+BF layout and allocator imported unchanged from round23. All original features retained. No test/negative-validation observations enter model fitting or soft-cut calibration.

## Matched training branches

Three initializations(seed1/2/3) per dataset, same initial train-only standardization. Each initialization performs the original100-iteration-max BCE/L2 warm start. For each physical budget, clone exactly that same warm model into:
- BCE100: unchanged warm baseline.
- BCE200: continue BCE for up to100 further L-BFGS-B iterations.
- FilterAware: continue the capped-filter surrogate for up to100 further L-BFGS-B iterations.

Same tolerances,L2 coefficient and maximal continuation iteration count. Function evaluations, stopping conditions and actual wall time are recorded; this is not an equal-wall-clock claim, and different loss scales can affect optimizer stopping. Do not retry nonconvergence or lengthen runs after observing results. Every final iterate is evaluated; no validation/test-selected checkpoint. PureBF at each budget remains a separate strong baseline.

## Differentiable surrogate, with clipping handled correctly

The network still outputs one scalar logit s. Define four ordered soft cuts from the warm model's training logits at20/40/60/80 percentiles, frozen for both branches. Temperature=max(0.25,training-logit IQR/4), fixed thereafter. Soft region memberships are differences of logistic CDFs at the four cuts; they are nonnegative and sum to1. There is no annealing or additional learned routing parameter.

For each class, sum memberships over TRAINING rows only and add one pseudo-count per region, normalizing separately into p and q. p estimates member-region probabilities for the full member set; q estimates static negative-region probabilities. n is the actual known full member count, used for BF budget scaling. This is an empirical static T=0 proxy, not a true future/cached residual distribution.

Subtract exact model arrays, normalization, common24B header and navigation/array overhead from the total budget to get available BF bits B; define beta=(ln2)^2 B/n. Solve the legal continuous inner problem:

`J(p,q)=min sum(q_r*exp(-z_r)), subject to sum(p_r*z_r)<=beta and z_r>=0`.

The log water level solves the active-set/clipped budget equation. Train loss=log J + unchanged L2 matrix penalty. The envelope derivative is dJ/dq_r=epsilon_r and dJ/dp_r=lambda*z_r, with epsilon=min(1,lambda*p/q). Backpropagate through the soft histograms and scalar MLP. This is not the untruncated KL lower bound and not a global optimum of model training. Tests compare the inner solver against an independent SLSQP convex optimization and the score/network gradients against numerical finite differences.

## Hard deployment and diagnosis

After both continuations finish for a budget, score original inputs with the actual native scorer, build the SAME frozen FastPLBF five-region structure from all known members and reserved validation negatives, then execute every member/test-pool key. Final hard deployment uses FastPLBF's own validation-driven thresholds, not the soft-training cuts. This deliberate surrogate-to-deployment gap is measured and disclosed.

Report soft training J, training-only hardened-cut J, final hard-PLBF FP, classification AUC, selected region thresholds, real owning-array model/BF bytes and native query costs. Better soft objective is not treated as a guarantee of better hard/test FP. No model directly rejects members; all members are inserted under the final routing, checked after construction and reload.

## Timing and matrix

Two datasets x3 seeds x2 budgets x(BCE100,BCE200,FilterAware,BF)=48 result records. Six fresh processes serially; single-thread before NumPy import, actual OpenBLAS andNumba thread count asserted. All training/model-scoring/filter-build times reported. BF reference records in this round are effectiveness/space controls; use round23 for its historical native timing and do not mislabel them freshly timed here.

Use the same100K-request native microbenchmark as round23:90K uniformly sampled test negatives+10K members. For each learned branch, three scorer-only and model+BF loop timings after warmup; standardization included, hashing/raw feature extraction excluded. Python FFI cost amortized over the loop. No database throughput, per-request p99 or cache-aware replay claim.

No data download or new dependency. Inputs/sources frozen before real runs. Failures stop, no automatic retry; memory pressure termination requires approval. All initializer outcomes, nonconvergence and performance regressions retained; seeds are model initializations on one data split, not independent workloads. No new significance, novelty, zero-tree guard or paper claim.

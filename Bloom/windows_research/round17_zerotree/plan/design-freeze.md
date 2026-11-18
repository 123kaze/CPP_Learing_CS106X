# Round17: RA6-Z, zero-tree candidate extension (2026-11-18)

## New method, not a rewrite of RA6

User request: introduce a zero-tree option so weak-model cases may automatically deploy an ordinary BF+cache. This is a post-hoc algorithm extension motivated by already observed TCP-only failures, named **RA6-Z**. Frozen RA6 and prior results are untouched. No new independent holdout or universal improvement is claimed.

The positive-tree candidate table is imported unchanged. Add t=0 at the same13 cache fractions. Each zero-tree candidate uses round12's actual owning BF array:4 uint64 header words (32B), one NumPy-array header and all remaining bits, with integer-k selection. No model, score segmentation, model-array headers or learned-DP metadata are charged. No evaluation-tail FP, replay outcome or baseline winner informs RA6-Z's choice.

## Zero-tree prediction and selection

The no-model BF is one score segment. Its per-key Good–Turing rates and unseen-key mass use the frozen summarizer, with h=[1]. Build one frozen Population over those rates for all cache fractions. Given a physical BF size m and integer k, use the same ideal finite-bit formula as round12, `(1-exp(-k*n/m))**k`, as its segment FPR. For each fraction, the first-stage prediction is `FPR * Population.misses([FPR],slots,setassoc=True)[0]`. There is no extra DP allocation to pay for one segment and no learned score to query.

Union the learned and13 zero-tree candidates, sort by(prediction,trees,frac), take the global TOP5 as before, build each and refine with frozen RA6 bucket_prediction using actual learning-key BF flags. For t=0, supply h=[1] and its exact integer-k ideal BF probability for the unseen mass. Pick the minimum(refined_prediction,shortlist_rank). Same Good–Turing, frozen finite-window approximation, cache semantics and top-five size as RA6; no retuning after formal outcomes.

A zero candidate is available but not forced into the top5. This intentionally tests the plain candidate-extension request. Adding a candidate does NOT guarantee never losing to BF+learning-ReplayCache on the evaluation tail: predictive ranking/refinement may misrank and the future may differ. Learned candidates may be displaced from the finite shortlist, so possible regression versus frozen RA6 must be reported. No later threshold, forced fallback, oracle gate or shortlist change in this round.

## Real no-model deployment

`ZeroTreeFilter` restores the BF from its owning buffer and queries via frozen hash/BF/CLOCK code with no model or feature input. Admission is a separate `feedback_absent` call; callers must obtain authoritative absence first. Indexed cache uses the complete member-hash safety index (budget-external,8B/member); fp64 keeps no member index in the deployed zero filter and still has collision-related false-negative limitations. Fixed member checks do not prove fp64 safe for arbitrary future keys.

Physical BF+cache bytes match round12 exactly. All selected zero-tree methods are replayed through a native bit-probing/CLOCK path on the complete known-negative test tail and must match the frozen simulator's FP/hit counts; all members must still be accepted with the resulting cache. This native oracle-known-negative routine is correctness-only, not claimed as a live backend feedback experiment. No feature extraction/model arrays are required by zero deployment.

Search still trains/scores learned candidates (this comparison uses already prepared frozen score caches). Selecting t=0 does not imply avoiding training during search, and does not represent Direct/no-filter RocksDB. Objective remains FP, not latency: the round16 negative database result is not resolved merely by adding t=0.

## Evaluation matrix:192 cache-specific cases

Both index and fp64; each dataset/cache combination in its own serial process,16 jobs total. Same old first25% learning, last75% cold-cache evaluation; actual original stream lengths for once/fresh/real traces. Full synthetic streams10M queries; original seeds0–4.

1. Primary weak-model cohort: all4 TCP-only datasets × their original4 budgets ×2 cache formats =32 cases. No selection of only favorable budgets.
2. Stronger-model controls: COD1024KiB, URL128KiB, CAIDA256KiB, Shalla1024KiB; Zipf1.0 over the full negative pool and every-key-once, seeds0–4, both cache formats =80 cases.
3. Known failure class: all original CAIDA budgets128/256/1024/2048 and Shalla256/1024/2048/4096, fresh-adversarial workload, seeds0–4, both formats =80 cases. Include all these settings, not just the previously losing30 eligible cases.

Eight methods per case (1536 rows):RA6-Z, originalRA6, Zero-Predict(t=0-only predictive top5), Gama(no zero), pureBF(no cache), BF+learning-ReplayCache, learned-onlyReplay, expandedReplay+Z. Zero-Predict diagnoses predictive cache-fraction error separately from the model/no-model branch choice. Replay+Z includes the entire13 zero candidates alongside all learned candidates and must be no worse on its LEARNING objective than either originalReplay or BF+ReplayCache; no such inequality is asserted for the future tail.

OriginalRA6/Gama/BF/BF+ReplayCache/Replay must reproduce round13's aligned archive exactly on tail FP and base-stream hashes. New selection never reads archive values; they are only post-selection assertions. There is no new hindsight/held-out tuning. Record selected trees/cache, byte breakdown, both ranking stages, shortlist composition, prediction, static flags, native checks, all counts and all unfavorable outcomes. Report all cases; do not hide near-zero counts through a favorable inclusion filter.

## Tests, timings and failure policy

Before formal freeze:7 synthetic unit tests cover layout/integer-k/budget, zero-only operation without learned-table access, invalid inputs, no-repeat static prediction, serialization/no-model deployment, feedback separation and required member index. CAIDA TCP16KiB pilot in both cache formats verifies originalRA6 reproduction when zero is disabled, all5 archived references and native zero execution. Pilot is excluded from formal results; parameters are not adjusted based on its favorable outcome.

Candidate-build costs for exact replay references are recorded separately per budget, because they are reused across workloads/seeds as in the archived runner. RA6/RA6-Z selection fields include their own summary/table/top-five builds; do not claim a selection-speed comparison from unequal timer boundaries or charge cached builds as free. This round's primary result is effectiveness/model fallback, not new full-construction timing. One thread, serial; existing input caches only, no implicit data preparation/training. Freeze source/input hashes before launch. Failed/partial jobs stop, no automatic retries or memory-pressure restart. Preserve old code, paper and adverse results.

# Round24: static feature-cell partition table, small follow-on test

User additionally requested trying direct partition learning and cost-weighted model training. This round tests only a deliberately small version of proposal B; it does NOT implement proposal A(cache-escape-weighted classifier training) or C(raw hashed URL n-grams). It follows the completed fixed-scorer screen on branch experiment/lightweight-scorers.

## Literature/scope before implementation

Tsitsiklis1993, Extremal Properties of Likelihood-Ratio Quantizers, IEEE Transactions on Communications41(4),550–558 exists (author publication list https://www.mit.edu/~jnt/publ.html). The accessible treatment https://arxiv.org/html/1910.11451v1 states a KL-maximizing likelihood-ratio quantizer result for two known laws and a fixed number of outputs. It does not prove that estimated cells plus a memory/inference penalty, clipping, integerBF or adaptive cache are jointly optimal. Original theorem full text not independently read in this trial.

PLBF/FastPLBF already optimizes score partitions and KL-related memory allocation. Prior “New Wine in an Old Bottle: Data-Aware Hash Functions for Bloom Filters” is a relevant lead for data-aware projections/hash partitioning; its PDF fetch failed certificate verification, so its exact overlap remains unverified. No novelty claim from this trial or from a changed model name.

## Frozen small prototype

Static cache=0,T=0 only. Same URL64/128KiB and CAIDA TCP16/32KiB, same input and split as round23. Use exactly2 prespecified existing features:
-URL:len,digits.
-TCP-only:src,dst as stored in the originalfloat32 arrays.
No new address encoding, raw IP-prefix parsing or raw URL feature extraction. The original negative-validation rows provide cell negative counts; only train rows fit quantile edges. All member keys are known BF construction input. This is direct partition/allocation fitting, unlike fitting a classifier only on the training subset; disclose the use of validation for routing and never call it an unseen calibration evaluation.

For each feature choose16 or32 quantile bins from train only; their Cartesian product gives256 or1024 cells. All cells including unobserved cells receive a deterministic route; out-of-range values land in boundary bins. Tied quantile edges use side=right consistently. Two-feature quantization is a limitation, not a claim that high-dimensional data or IP geometry is solved.

Cell densities are (member_count+1)/(n+cells) and (validation_negative_count+1)/(v+cells). Sort cells by the estimated ratio ascending, then apply frozen DP over that order with five output regions, original integer BF allocation/hash probes and original count smoothing. This is estimated smoothed ratio partitioning; no normalized current-cache residual mass, no EB fit, no raw infinite ratio and no unseen-distribution guarantee.

The cell->region lookup is genuinely packed at3bits/cell into uint64 words. Charge the FULL required representation:24B layout/feature header plus array header, quantile edges for both features, packed lookup with array header, region kind/offset/m/k arrays, BF bitmap and headers. No tree or classifier. Store complete cell routing, not a sparse dictionary pretending keys/unknown-lookup overhead are free. All members must be accepted; native quantization+table+BF output must equal frozen bitmap querying for all rows; reloaded arrays checked in unit tests.

KL is diagnostic on the actual final five regions and explicitly smoothed estimated densities. It is not a deployed-FP guarantee or a resource-aware global optimum. Do not claim the original “maxKL minus model bytes minus latency” expression is exact after clipping or cache feedback.

## Measurements

Each of2 datasets x2 grid resolutions x2 budgets rebuilt3 times =24 rows. Same100K request indices as round23 (90K negatives,10K members). Three native-loop timing repeats per build after warmup: router-only and router+BF. Include bin search, packed table access and BF probes; no precomputed region lookup by key. Raw feature extraction and key hashing remain shared prepared inputs and are outside timing. These are batch-amortized native loops, not Python scalar API or database latency.

Report real bytes, FP count, ratio to corresponding round23 pureBF, fit/build time, all repeated timings, populated cell counts and finite-bin behavior. No selecting a winning grid before reporting others. FP from all three deterministic builds must agree; slower/failing configurations retained.

All single-threaded, serial after round23, no frozen edits/dependency installation/new data/paper changes. Fail without automatic retry. Do not compare these new stage times as a controlled paired speedup against historical timings; use them as an initial architecture screening.

## Deferred proposal A/C

A requires defining residual weights for training negatives, which are disjoint from the learning-query pool. Key-level future escape counts are unknown and depend on the current model/cache; simply assigning evaluation-derived weights leaks information. A mapped weighting proxy and a same-capacity control need a separate freeze.

C requires raw URL strings and actual n-gram extraction/hash-table costs. The current18 precomputed features cannot be relabeled as n-grams. It is not part of this run.

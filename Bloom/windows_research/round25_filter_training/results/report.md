# Same MLP8: static filter-aware training versus classification training

Same model parameter count, original features, training split and native scoring/filter implementation. Three different initialization seeds, each shared between branches. Common BCE warm start of up to100 iterations; BCE200 and FilterAware each receive up to100 further iterations. Different function-evaluation/wall costs are reported, not assumed equal. No negative cache, quantization or global joint optimality claim.

| Dataset | KiB | Method | Test FP (seeds1/2/3) | Median FP | Model bytes incl. headers | Native query ns | Charged training s | Continuation converged |
|---|---:|---|---|---:|---:|---:|---:|---|
| url | 64 | BCE100 | 1763/1705/1938 | 1763 | 1688 | 250.5 | 1.176 | warm baseline |
| url | 64 | BCE200 | 1553/1366/1889 | 1553 | 1688 | 253.5 | 2.371 | 0/3 |
| url | 64 | FilterAware | 1690/1422/1644 | 1644 | 1688 | 252.5 | 4.115 | 0/3 |
| url | 64 | BF | 106302/106302/106302 | 106302 | 0 | not timed here | not timed here | n/a |
| url | 128 | BCE100 | 364/428/435 | 428 | 1688 | 269.7 | 1.176 | warm baseline |
| url | 128 | BCE200 | 357/368/457 | 368 | 1688 | 263.3 | 2.384 | 0/3 |
| url | 128 | FilterAware | 325/306/366 | 325 | 1688 | 273.3 | 4.037 | 0/3 |
| url | 128 | BF | 32377/32377/32377 | 32377 | 0 | not timed here | not timed here | n/a |
| caida_tcp_flow | 16 | BCE100 | 45139/45195/45139 | 45139 | 408 | 49.9 | 0.199 | warm baseline |
| caida_tcp_flow | 16 | BCE200 | 45139/45195/45139 | 45139 | 408 | 48.6 | 0.204 | 3/3 |
| caida_tcp_flow | 16 | FilterAware | 45195/45195/45285 | 45195 | 408 | 47.6 | 0.231 | 3/3 |
| caida_tcp_flow | 16 | BF | 41884/41884/41884 | 41884 | 0 | not timed here | not timed here | n/a |
| caida_tcp_flow | 32 | BCE100 | 27358/27266/27358 | 27358 | 408 | 53.3 | 0.199 | warm baseline |
| caida_tcp_flow | 32 | BCE200 | 27358/27266/27358 | 27358 | 408 | 52.4 | 0.204 | 3/3 |
| caida_tcp_flow | 32 | FilterAware | 27266/27266/27224 | 27266 | 408 | 54.7 | 0.230 | 3/3 |
| caida_tcp_flow | 32 | BF | 25922/25922/25922 | 25922 | 0 | not timed here | not timed here | n/a |

## Soft objective versus actual deployment

| Dataset | KiB | Method | Median soft training J | Median hardened training J | Median actual test FPR |
|---|---:|---|---:|---:|---:|
| url | 64 | BCE100 | 0.07609186 | 0.00764578 | 0.00514504 |
| url | 64 | BCE200 | 0.07199907 | 0.00637498 | 0.00453219 |
| url | 64 | FilterAware | 0.00447268 | 0.00369658 | 0.00479776 |
| url | 128 | BCE100 | 0.02024198 | 0.00151456 | 0.00124905 |
| url | 128 | BCE200 | 0.01876064 | 0.00119924 | 0.00107395 |
| url | 128 | FilterAware | 0.00053628 | 0.00041922 | 0.00094846 |
| caida_tcp_flow | 16 | BCE100 | 0.63844334 | 0.63839679 | 0.67455206 |
| caida_tcp_flow | 16 | BCE200 | 0.63844334 | 0.63839679 | 0.67455206 |
| caida_tcp_flow | 16 | FilterAware | 0.63844337 | 0.63839679 | 0.67538891 |
| caida_tcp_flow | 32 | BCE100 | 0.39121036 | 0.39118185 | 0.40883483 |
| caida_tcp_flow | 32 | BCE200 | 0.39121036 | 0.39118185 | 0.40883483 |
| caida_tcp_flow | 32 | FilterAware | 0.39121038 | 0.39118185 | 0.40745999 |

## Interpretation

- URL128KiB is the positive local result:all3 FilterAware initializations lower actual FP than continued BCE at identical model size. URL64KiB improves only1 of3. Neither budget establishes a universal advantage or significance with three model seeds.
- TCP-only learned branches remain worse than plainBF. All scores can be nearly uninformative on the current address encoding; changing the training objective does not guarantee new information.
- URL continuation optimizers hit the prespecified100-iteration limit in both branches. These are fixed-compute-budget trials, not converged globally optimal models. Retain function evaluations, gradient norms and wall times; do not claim equal time from equal iteration ceilings.
- A lower soft proxy does not imply proportionally lower deployed FP. Training uses smoothed soft-region class histograms and an estimated capped continuous BF objective; deployment uses hard scores, validation-driven FastPLBF partitions and integer BF probing. The hard-training diagnostic fixes the soft training cuts, so it is not identical to final deployment routing either.
- Mean/std and soft-cut/temperature calibration use only training observations. Both branches start from exactly the same warm weights. Test/negative-validation values do not select model checkpoints, losses or hyperparameters. All models are evaluated even when worse.
- Model bytes, normalization and navigation/array overhead are charged before BF bits. All members are inserted and verified in final regions. Native scoring matches reference arithmetic, every key matches frozen BF flags, and reloaded arrays reproduce all query decisions.
- Native timing uses fixed100K requests in a compiled loop with batch-amortized call overhead. Standardization is included; raw feature extraction, key hashing, Python scalar API overhead and database access are not. No p99 or end-to-end throughput result is asserted.
- No cache-aware residual weights, direct multi-output router, quantization, KL threshold or zero-tree selection algorithm is part of this experiment. These are separate possible next steps, not completed claims. Existing RA6/paper files and old frozen experiments remain unchanged.

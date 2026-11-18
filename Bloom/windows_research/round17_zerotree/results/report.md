# RA6-Z: adding physically accounted zero-tree candidates

192 post-hoc cases, two cache formats, eight methods. The original learned path is frozen. New RA6-Z merges13 zero-tree candidates into the global top-five predictive shortlist, then uses the same actual-bucket refinement. Selection sees learning statistics, never evaluation-tail outcomes. All five original reference methods reproduce round13 exactly.

Ratios are per-case `(FP_method+1)/(FP_reference+1)` before taking medians. All cases are retained, including low counts. Zero-selected counts refer to the numerator method. These cases share datasets/models and are not independent statistical samples.

| Cache | Cohort | Method / reference | Cases | Zero selected | Median FP ratio | Win/tie/loss | Worst ratio |
|---|---|---|---:|---:|---:|---|---:|
| index | weak_tcp | RA6-Z / BF+ReplayCache | 16 | 8 | 1.0084 | 6/2/8 | 1.1283 |
| index | weak_tcp | RA6-Z / RA6 | 16 | 8 | 1.0000 | 7/8/1 | 1.0035 |
| index | weak_tcp | RA6-Z / Replay+Z | 16 | 8 | 1.0084 | 6/2/8 | 1.1283 |
| index | weak_tcp | RA6 / BF+ReplayCache | 16 | 0 | 1.0629 | 3/0/13 | 1.1283 |
| index | weak_tcp | Zero-Predict / BF+ReplayCache | 16 | 16 | 1.0000 | 7/7/2 | 1.0792 |
| index | model_control | RA6-Z / BF+ReplayCache | 40 | 0 | 0.0114 | 40/0/0 | 0.2260 |
| index | model_control | RA6-Z / RA6 | 40 | 0 | 1.0000 | 0/40/0 | 1.0000 |
| index | model_control | RA6-Z / Replay+Z | 40 | 0 | 1.0001 | 19/1/20 | 1.2444 |
| index | model_control | RA6 / BF+ReplayCache | 40 | 0 | 0.0114 | 40/0/0 | 0.2260 |
| index | model_control | Zero-Predict / BF+ReplayCache | 40 | 40 | 1.0000 | 6/31/3 | 1.0594 |
| index | fresh_adversarial | RA6-Z / BF+ReplayCache | 40 | 0 | 1.2627 | 10/0/30 | 1.6329 |
| index | fresh_adversarial | RA6-Z / RA6 | 40 | 0 | 1.0000 | 0/40/0 | 1.0000 |
| index | fresh_adversarial | RA6-Z / Replay+Z | 40 | 0 | 1.2627 | 10/0/30 | 1.6329 |
| index | fresh_adversarial | RA6 / BF+ReplayCache | 40 | 0 | 1.2627 | 10/0/30 | 1.6329 |
| index | fresh_adversarial | Zero-Predict / BF+ReplayCache | 40 | 40 | 0.9995 | 20/10/10 | 1.0793 |
| fp64 | weak_tcp | RA6-Z / BF+ReplayCache | 16 | 9 | 1.0149 | 6/2/8 | 1.1392 |
| fp64 | weak_tcp | RA6-Z / RA6 | 16 | 9 | 0.9932 | 8/7/1 | 1.0871 |
| fp64 | weak_tcp | RA6-Z / Replay+Z | 16 | 9 | 1.0149 | 6/2/8 | 1.1392 |
| fp64 | weak_tcp | RA6 / BF+ReplayCache | 16 | 0 | 1.0526 | 3/0/13 | 1.1410 |
| fp64 | weak_tcp | Zero-Predict / BF+ReplayCache | 16 | 16 | 0.9979 | 9/5/2 | 1.0696 |
| fp64 | model_control | RA6-Z / BF+ReplayCache | 40 | 0 | 0.0116 | 40/0/0 | 0.2260 |
| fp64 | model_control | RA6-Z / RA6 | 40 | 0 | 1.0000 | 0/40/0 | 1.0000 |
| fp64 | model_control | RA6-Z / Replay+Z | 40 | 0 | 0.9963 | 23/0/17 | 1.2168 |
| fp64 | model_control | RA6 / BF+ReplayCache | 40 | 0 | 0.0116 | 40/0/0 | 0.2260 |
| fp64 | model_control | Zero-Predict / BF+ReplayCache | 40 | 40 | 1.0000 | 9/27/4 | 1.0282 |
| fp64 | fresh_adversarial | RA6-Z / BF+ReplayCache | 40 | 0 | 1.2639 | 10/0/30 | 1.6266 |
| fp64 | fresh_adversarial | RA6-Z / RA6 | 40 | 0 | 1.0000 | 0/40/0 | 1.0000 |
| fp64 | fresh_adversarial | RA6-Z / Replay+Z | 40 | 0 | 1.2639 | 10/0/30 | 1.6266 |
| fp64 | fresh_adversarial | RA6 / BF+ReplayCache | 40 | 0 | 1.2639 | 10/0/30 | 1.6266 |
| fp64 | fresh_adversarial | Zero-Predict / BF+ReplayCache | 40 | 40 | 0.9994 | 20/10/10 | 1.0793 |

## All TCP-only settings

| Cache | Dataset | KiB | Original RA6 FP | BF+ReplayCache FP | RA6-Z FP | RA6-Z trees | Cache fraction | Expanded Replay FP |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| index | caida_tcp_flow | 16 | 98385 | 92346 | 90441 | 0 | 0.2 | 92346 |
| index | caida_tcp_flow | 32 | 55050 | 50568 | 50203 | 0 | 0.2 | 50568 |
| index | caida_tcp_flow | 63 | 15576 | 14077 | 14077 | 0 | 0.2 | 14077 |
| index | caida_tcp_flow | 189 | 173 | 187 | 145 | 0 | 0.015 | 187 |
| fp64 | caida_tcp_flow | 16 | 103163 | 97487 | 94787 | 0 | 0.2 | 97487 |
| fp64 | caida_tcp_flow | 32 | 57427 | 52953 | 56641 | 0 | 0.3 | 52953 |
| fp64 | caida_tcp_flow | 63 | 18554 | 16859 | 16859 | 0 | 0.2 | 16859 |
| fp64 | caida_tcp_flow | 189 | 177 | 155 | 155 | 0 | 0.015 | 155 |
| index | mawi2020_tcp_flow | 32 | 116256 | 109636 | 116256 | 1 | 0.05 | 109636 |
| index | mawi2020_tcp_flow | 64 | 68394 | 67267 | 68394 | 1 | 0.015 | 67267 |
| index | mawi2020_tcp_flow | 127 | 25760 | 23993 | 23993 | 0 | 0.015 | 23993 |
| index | mawi2020_tcp_flow | 381 | 485 | 528 | 454 | 0 | 0.005 | 546 |
| fp64 | mawi2020_tcp_flow | 32 | 117326 | 112953 | 117326 | 1 | 0.05 | 112953 |
| fp64 | mawi2020_tcp_flow | 64 | 67627 | 68089 | 67627 | 1 | 0.02 | 68089 |
| fp64 | mawi2020_tcp_flow | 127 | 25909 | 24954 | 25909 | 1 | 0.015 | 24954 |
| fp64 | mawi2020_tcp_flow | 381 | 530 | 498 | 453 | 0 | 0.005 | 498 |
| index | mawi2021_tcp_flow | 21 | 74281 | 65835 | 74281 | 1 | 0.02 | 65835 |
| index | mawi2021_tcp_flow | 41 | 41727 | 40014 | 41727 | 1 | 0.05 | 40014 |
| index | mawi2021_tcp_flow | 81 | 15688 | 14558 | 14388 | 0 | 0.05 | 14558 |
| index | mawi2021_tcp_flow | 242 | 284 | 264 | 285 | 0 | 0.005 | 264 |
| fp64 | mawi2021_tcp_flow | 21 | 76444 | 67103 | 76444 | 1 | 0.015 | 67103 |
| fp64 | mawi2021_tcp_flow | 41 | 42211 | 40858 | 42211 | 1 | 0.015 | 40858 |
| fp64 | mawi2021_tcp_flow | 81 | 16087 | 14574 | 15009 | 0 | 0.05 | 14574 |
| fp64 | mawi2021_tcp_flow | 242 | 299 | 301 | 242 | 0 | 0.005 | 301 |
| index | mawi2022_tcp_flow | 32 | 104022 | 96782 | 104022 | 2 | 0.1 | 96782 |
| index | mawi2022_tcp_flow | 64 | 58339 | 55735 | 58339 | 1 | 0.1 | 55735 |
| index | mawi2022_tcp_flow | 128 | 21336 | 20252 | 21336 | 2 | 0.05 | 20252 |
| index | mawi2022_tcp_flow | 382 | 376 | 432 | 376 | 2 | 0.002 | 432 |
| fp64 | mawi2022_tcp_flow | 32 | 105636 | 97926 | 105636 | 1 | 0.1 | 97926 |
| fp64 | mawi2022_tcp_flow | 64 | 60362 | 57779 | 60362 | 1 | 0.1 | 57779 |
| fp64 | mawi2022_tcp_flow | 128 | 22004 | 21016 | 20937 | 0 | 0.05 | 21016 |
| fp64 | mawi2022_tcp_flow | 382 | 378 | 440 | 411 | 0 | 0.002 | 440 |

## Remaining failures and regressions

| Cache | Dataset | KiB | Workload | Seed | New FP | Old RA6 FP | BF+cache FP | New trees |
|---|---|---:|---|---:|---:|---:|---:|---:|
| fp64 | caida_tcp_flow | 32 | 真实轨迹 | 0 | 56641 | 57427 | 52953 | 0 |
| index | mawi2020_tcp_flow | 32 | 真实轨迹 | 0 | 116256 | 116256 | 109636 | 1 |
| index | mawi2020_tcp_flow | 64 | 真实轨迹 | 0 | 68394 | 68394 | 67267 | 1 |
| fp64 | mawi2020_tcp_flow | 32 | 真实轨迹 | 0 | 117326 | 117326 | 112953 | 1 |
| fp64 | mawi2020_tcp_flow | 127 | 真实轨迹 | 0 | 25909 | 25909 | 24954 | 1 |
| index | mawi2021_tcp_flow | 21 | 真实轨迹 | 0 | 74281 | 74281 | 65835 | 1 |
| index | mawi2021_tcp_flow | 41 | 真实轨迹 | 0 | 41727 | 41727 | 40014 | 1 |
| index | mawi2021_tcp_flow | 242 | 真实轨迹 | 0 | 285 | 284 | 264 | 0 |
| fp64 | mawi2021_tcp_flow | 21 | 真实轨迹 | 0 | 76444 | 76444 | 67103 | 1 |
| fp64 | mawi2021_tcp_flow | 41 | 真实轨迹 | 0 | 42211 | 42211 | 40858 | 1 |
| fp64 | mawi2021_tcp_flow | 81 | 真实轨迹 | 0 | 15009 | 16087 | 14574 | 0 |
| index | mawi2022_tcp_flow | 32 | 真实轨迹 | 0 | 104022 | 104022 | 96782 | 2 |
| index | mawi2022_tcp_flow | 64 | 真实轨迹 | 0 | 58339 | 58339 | 55735 | 1 |
| index | mawi2022_tcp_flow | 128 | 真实轨迹 | 0 | 21336 | 21336 | 20252 | 2 |
| fp64 | mawi2022_tcp_flow | 32 | 真实轨迹 | 0 | 105636 | 105636 | 97926 | 1 |
| fp64 | mawi2022_tcp_flow | 64 | 真实轨迹 | 0 | 60362 | 60362 | 57779 | 1 |
| fp64 | mawi2022_tcp_flow | 382 | 真实轨迹 | 0 | 411 | 378 | 440 | 0 |
| index | caida | 256 | 全新对抗 | 0 | 23320 | 23320 | 16225 | 160 |
| index | caida | 256 | 全新对抗 | 1 | 23320 | 23320 | 16225 | 160 |
| index | caida | 256 | 全新对抗 | 2 | 23320 | 23320 | 16225 | 160 |
| index | caida | 256 | 全新对抗 | 3 | 23320 | 23320 | 16225 | 160 |
| index | caida | 256 | 全新对抗 | 4 | 23320 | 23320 | 16225 | 160 |
| index | caida | 128 | 全新对抗 | 0 | 35690 | 35690 | 25543 | 96 |
| index | caida | 128 | 全新对抗 | 1 | 35690 | 35690 | 25543 | 96 |
| index | caida | 128 | 全新对抗 | 2 | 35690 | 35690 | 25543 | 96 |
| index | caida | 128 | 全新对抗 | 3 | 35690 | 35690 | 25543 | 96 |
| index | caida | 128 | 全新对抗 | 4 | 35690 | 35690 | 25543 | 96 |
| fp64 | caida | 256 | 全新对抗 | 0 | 23320 | 23320 | 16299 | 160 |
| fp64 | caida | 256 | 全新对抗 | 1 | 23320 | 23320 | 16299 | 160 |
| fp64 | caida | 256 | 全新对抗 | 2 | 23320 | 23320 | 16299 | 160 |
| fp64 | caida | 256 | 全新对抗 | 3 | 23320 | 23320 | 16299 | 160 |
| fp64 | caida | 256 | 全新对抗 | 4 | 23320 | 23320 | 16299 | 160 |
| fp64 | caida | 128 | 全新对抗 | 0 | 35690 | 35690 | 25543 | 96 |
| fp64 | caida | 128 | 全新对抗 | 1 | 35690 | 35690 | 25543 | 96 |
| fp64 | caida | 128 | 全新对抗 | 2 | 35690 | 35690 | 25543 | 96 |
| fp64 | caida | 128 | 全新对抗 | 3 | 35690 | 35690 | 25543 | 96 |
| fp64 | caida | 128 | 全新对抗 | 4 | 35690 | 35690 | 25543 | 96 |
| index | shalla | 1024 | 全新对抗 | 0 | 15265 | 15265 | 9348 | 48 |
| index | shalla | 1024 | 全新对抗 | 1 | 15265 | 15265 | 9348 | 48 |
| index | shalla | 1024 | 全新对抗 | 2 | 15265 | 15265 | 9348 | 48 |
| index | shalla | 1024 | 全新对抗 | 3 | 15265 | 15265 | 9348 | 48 |
| index | shalla | 1024 | 全新对抗 | 4 | 15265 | 15265 | 9348 | 48 |
| index | shalla | 256 | 全新对抗 | 0 | 37367 | 37367 | 28325 | 12 |
| index | shalla | 256 | 全新对抗 | 1 | 37367 | 37367 | 28325 | 12 |
| index | shalla | 256 | 全新对抗 | 2 | 37367 | 37367 | 28325 | 12 |
| index | shalla | 256 | 全新对抗 | 3 | 37367 | 37367 | 28325 | 12 |
| index | shalla | 256 | 全新对抗 | 4 | 37367 | 37367 | 28325 | 12 |
| index | shalla | 2048 | 全新对抗 | 0 | 2947 | 2947 | 2443 | 48 |
| index | shalla | 2048 | 全新对抗 | 1 | 2947 | 2947 | 2443 | 48 |
| index | shalla | 2048 | 全新对抗 | 2 | 2947 | 2947 | 2443 | 48 |
| index | shalla | 2048 | 全新对抗 | 3 | 2947 | 2947 | 2443 | 48 |
| index | shalla | 2048 | 全新对抗 | 4 | 2947 | 2947 | 2443 | 48 |
| index | shalla | 4096 | 全新对抗 | 0 | 196 | 196 | 163 | 48 |
| index | shalla | 4096 | 全新对抗 | 1 | 196 | 196 | 163 | 48 |
| index | shalla | 4096 | 全新对抗 | 2 | 196 | 196 | 163 | 48 |
| index | shalla | 4096 | 全新对抗 | 3 | 196 | 196 | 163 | 48 |
| index | shalla | 4096 | 全新对抗 | 4 | 196 | 196 | 163 | 48 |
| fp64 | shalla | 1024 | 全新对抗 | 0 | 15265 | 15265 | 9384 | 48 |
| fp64 | shalla | 1024 | 全新对抗 | 1 | 15265 | 15265 | 9384 | 48 |
| fp64 | shalla | 1024 | 全新对抗 | 2 | 15265 | 15265 | 9384 | 48 |
| fp64 | shalla | 1024 | 全新对抗 | 3 | 15265 | 15265 | 9384 | 48 |
| fp64 | shalla | 1024 | 全新对抗 | 4 | 15265 | 15265 | 9384 | 48 |
| fp64 | shalla | 256 | 全新对抗 | 0 | 37367 | 37367 | 28276 | 12 |
| fp64 | shalla | 256 | 全新对抗 | 1 | 37367 | 37367 | 28276 | 12 |
| fp64 | shalla | 256 | 全新对抗 | 2 | 37367 | 37367 | 28276 | 12 |
| fp64 | shalla | 256 | 全新对抗 | 3 | 37367 | 37367 | 28276 | 12 |
| fp64 | shalla | 256 | 全新对抗 | 4 | 37367 | 37367 | 28276 | 12 |
| fp64 | shalla | 2048 | 全新对抗 | 0 | 2947 | 2947 | 2443 | 48 |
| fp64 | shalla | 2048 | 全新对抗 | 1 | 2947 | 2947 | 2443 | 48 |
| fp64 | shalla | 2048 | 全新对抗 | 2 | 2947 | 2947 | 2443 | 48 |
| fp64 | shalla | 2048 | 全新对抗 | 3 | 2947 | 2947 | 2443 | 48 |
| fp64 | shalla | 2048 | 全新对抗 | 4 | 2947 | 2947 | 2443 | 48 |
| fp64 | shalla | 4096 | 全新对抗 | 0 | 196 | 196 | 163 | 48 |
| fp64 | shalla | 4096 | 全新对抗 | 1 | 196 | 196 | 163 | 48 |
| fp64 | shalla | 4096 | 全新对抗 | 2 | 196 | 196 | 163 | 48 |
| fp64 | shalla | 4096 | 全新对抗 | 3 | 196 | 196 | 163 | 48 |
| fp64 | shalla | 4096 | 全新对抗 | 4 | 196 | 196 | 163 | 48 |

## Where the remaining TCP-only losses occur

| Cache | No zero-tree candidate in top5 | Zero built, learned wins refinement | Zero chosen, different cache fraction from BF replay |
|---|---:|---:|---:|
| index | 5 | 2 | 1 |
| fp64 | 4 | 2 | 2 |

This is a stage-location diagnosis, not a proof of causal loss decomposition. Expanded candidate availability does not remove prediction error or future distribution change. Full case details are in diagnostics.json.

## Scope and interpretation

- This is RA6-Z, a new method extension motivated by already observed weak-model failures—not a retroactive rewrite or independent holdout validation of RA6. Frozen methods, parameters and original unfavorable results remain available.
- Zero-tree consumes only the actual BF owning array and chosen cache; model bytes are zero. A standalone reloaded ZeroTreeFilter takes hashes, not features/model arrays, and has a separate authoritative-absence feedback interface. Full native BF/CLOCK tail counts match the frozen simulator for every selected zero-tree result.
- Search still evaluates learned models; choosing zero trees at deployment does not eliminate their training/scoring cost during search. Zero-tree also is not a Direct/no-filter database candidate, and minimizing FP is not minimizing database latency. The round16 negative database result is not resolved by this experiment.
- Merely adding candidates guarantees neither an expanded predictive shortlist containing the old winner nor a future-tail improvement. Zero-Predict diagnoses pure-BF prediction separately; expanded Replay+Z is guaranteed no worse only on its learning replay objective, not on its evaluation tail.
- Exact Replay candidate-build costs are recorded separately and reused per budget; predictive timing includes its own table/top-five builds. Do not quote these unequal-boundary fields as a new selection-speed claim. Models/scores are read from frozen caches, not freshly trained for this effectiveness comparison.
- Indexed negative caches require a member safety index outside the filter budget. The deployed fp64 zero-tree path needs no such index, but collision-related FN limitations remain; the experiment loader still prepares legacy state. Fixed-input member checks are not a guarantee for arbitrary future keys.
- Strong-model controls cover COD/URL/CAIDA/Shalla at one prespecified middle budget each, Zipf1.0 and every-key-once. Fresh-adversarial controls cover all original CAIDA/Shalla budgets. These are not a replacement for the full original1146-case main table.
- The original fresh-adversarial generator is deterministic with respect to seed; its five seed labels do not create five independent traces. Other case sharing also precludes treating192 cases as192 independent trials. No new significance test is asserted.
- Seven synthetic unit checks and two real-cache-format pilot cases precede the formal freeze; the pilot verifies the zero-disabled variant exactly reproduces original RA6. No tuning follows the formal result.

# RA6-ZGate: explicit no-model protection through learning replay

192 cases;13 BF/cache configurations plus one repaired RA6 finalist. The choice uses only exact learning FP; ties select the no-model winner. All192 learning inequalities were checked. Future-tail outcomes below are not used to select candidates.

| Cache | Cohort | Reference | Cases | Zero selected | Tail FP ratio median | Win/tie/loss | Worst ratio |
|---|---|---|---:|---:|---:|---|---:|
| index | weak_tcp | BF+ReplayCache | 16 | 16 | 1.000000 | 0/16/0 | 1.000000 |
| index | weak_tcp | RA6-GT19 | 16 | 16 | 0.940838 | 13/0/3 | 1.148541 |
| index | model_control | BF+ReplayCache | 40 | 0 | 0.011353 | 40/0/0 | 0.226034 |
| index | model_control | RA6-GT19 | 40 | 0 | 1.000000 | 0/40/0 | 1.000000 |
| index | fresh_adversarial | BF+ReplayCache | 40 | 40 | 1.000000 | 0/40/0 | 1.000000 |
| index | fresh_adversarial | RA6-GT19 | 40 | 40 | 0.793532 | 30/0/10 | 1.441273 |
| fp64 | weak_tcp | BF+ReplayCache | 16 | 16 | 1.000000 | 0/16/0 | 1.000000 |
| fp64 | weak_tcp | RA6-GT19 | 16 | 16 | 0.950041 | 13/0/3 | 1.163588 |
| fp64 | model_control | BF+ReplayCache | 40 | 0 | 0.011604 | 40/0/0 | 0.226034 |
| fp64 | model_control | RA6-GT19 | 40 | 0 | 1.000000 | 0/40/0 | 1.000000 |
| fp64 | fresh_adversarial | BF+ReplayCache | 40 | 40 | 1.000000 | 0/40/0 | 1.000000 |
| fp64 | fresh_adversarial | RA6-GT19 | 40 | 40 | 0.792877 | 30/0/10 | 1.457143 |

## TCP-only: training and future counted separately

| Cache | Dataset | KiB | Family | Learn BF | Learn RA6 | Learn chosen | Tail BF | Tail RA6 | Tail chosen |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| index | caida_tcp_flow | 16 | zero | 39338 | 43430 | 39338 | 92346 | 98385 | 92346 |
| index | caida_tcp_flow | 32 | zero | 22469 | 24766 | 22469 | 50568 | 55050 | 50568 |
| index | caida_tcp_flow | 63 | zero | 6682 | 7405 | 6682 | 14077 | 15576 | 14077 |
| index | caida_tcp_flow | 189 | zero | 73 | 93 | 73 | 187 | 173 | 187 |
| fp64 | caida_tcp_flow | 16 | zero | 40740 | 44972 | 40740 | 97487 | 103163 | 97487 |
| fp64 | caida_tcp_flow | 32 | zero | 23391 | 25251 | 23391 | 52953 | 57427 | 52953 |
| fp64 | caida_tcp_flow | 63 | zero | 7689 | 8128 | 7689 | 16859 | 18554 | 16859 |
| fp64 | caida_tcp_flow | 189 | zero | 75 | 93 | 75 | 155 | 177 | 155 |
| index | mawi2020_tcp_flow | 32 | zero | 45943 | 49111 | 45943 | 109636 | 116256 | 109636 |
| index | mawi2020_tcp_flow | 64 | zero | 28064 | 28681 | 28064 | 67267 | 68394 | 67267 |
| index | mawi2020_tcp_flow | 127 | zero | 10358 | 10918 | 10358 | 23993 | 25760 | 23993 |
| index | mawi2020_tcp_flow | 381 | zero | 192 | 196 | 192 | 528 | 485 | 528 |
| fp64 | mawi2020_tcp_flow | 32 | zero | 46352 | 49557 | 46352 | 112953 | 117326 | 112953 |
| fp64 | mawi2020_tcp_flow | 64 | zero | 28327 | 28849 | 28327 | 68089 | 67627 | 68089 |
| fp64 | mawi2020_tcp_flow | 127 | zero | 10368 | 10858 | 10368 | 24954 | 25909 | 24954 |
| fp64 | mawi2020_tcp_flow | 381 | zero | 188 | 216 | 188 | 498 | 530 | 498 |
| index | mawi2021_tcp_flow | 21 | zero | 38284 | 43273 | 38284 | 65835 | 74281 | 65835 |
| index | mawi2021_tcp_flow | 41 | zero | 23413 | 24657 | 23413 | 40014 | 41727 | 40014 |
| index | mawi2021_tcp_flow | 81 | zero | 8506 | 9258 | 8506 | 14558 | 15688 | 14558 |
| index | mawi2021_tcp_flow | 242 | zero | 154 | 165 | 154 | 264 | 284 | 264 |
| fp64 | mawi2021_tcp_flow | 21 | zero | 38725 | 43996 | 38725 | 67103 | 76444 | 67103 |
| fp64 | mawi2021_tcp_flow | 41 | zero | 23545 | 24720 | 23545 | 40858 | 42211 | 40858 |
| fp64 | mawi2021_tcp_flow | 81 | zero | 8511 | 9538 | 8511 | 14574 | 16087 | 14574 |
| fp64 | mawi2021_tcp_flow | 242 | zero | 154 | 166 | 154 | 301 | 299 | 301 |
| index | mawi2022_tcp_flow | 32 | zero | 37912 | 41362 | 37912 | 96782 | 104022 | 96782 |
| index | mawi2022_tcp_flow | 64 | zero | 22762 | 23498 | 22762 | 55735 | 58339 | 55735 |
| index | mawi2022_tcp_flow | 128 | zero | 8224 | 8829 | 8224 | 20252 | 21336 | 20252 |
| index | mawi2022_tcp_flow | 382 | zero | 142 | 177 | 142 | 432 | 376 | 432 |
| fp64 | mawi2022_tcp_flow | 32 | zero | 38394 | 41480 | 38394 | 97926 | 105636 | 97926 |
| fp64 | mawi2022_tcp_flow | 64 | zero | 23205 | 24333 | 23205 | 57779 | 60362 | 57779 |
| fp64 | mawi2022_tcp_flow | 128 | zero | 8158 | 8792 | 8158 | 21016 | 22004 | 21016 |
| fp64 | mawi2022_tcp_flow | 382 | zero | 142 | 170 | 142 | 440 | 378 | 440 |

## All future-tail regressions against either reference

| Cache | Dataset | KiB | Workload | Seed | Family | Chosen FP | BF FP | RA6 FP |
|---|---|---:|---|---:|---|---:|---:|---:|
| index | caida_tcp_flow | 189 | 真实轨迹 | 0 | zero | 187 | 187 | 173 |
| index | mawi2020_tcp_flow | 381 | 真实轨迹 | 0 | zero | 528 | 528 | 485 |
| fp64 | mawi2020_tcp_flow | 64 | 真实轨迹 | 0 | zero | 68089 | 68089 | 67627 |
| fp64 | mawi2021_tcp_flow | 242 | 真实轨迹 | 0 | zero | 301 | 301 | 299 |
| index | mawi2022_tcp_flow | 382 | 真实轨迹 | 0 | zero | 432 | 432 | 376 |
| fp64 | mawi2022_tcp_flow | 382 | 真实轨迹 | 0 | zero | 440 | 440 | 378 |
| index | caida | 1024 | 全新对抗 | 0 | zero | 1312 | 1312 | 910 |
| index | caida | 1024 | 全新对抗 | 1 | zero | 1312 | 1312 | 910 |
| index | caida | 1024 | 全新对抗 | 2 | zero | 1312 | 1312 | 910 |
| index | caida | 1024 | 全新对抗 | 3 | zero | 1312 | 1312 | 910 |
| index | caida | 1024 | 全新对抗 | 4 | zero | 1312 | 1312 | 910 |
| index | caida | 2048 | 全新对抗 | 0 | zero | 43 | 43 | 34 |
| index | caida | 2048 | 全新对抗 | 1 | zero | 43 | 43 | 34 |
| index | caida | 2048 | 全新对抗 | 2 | zero | 43 | 43 | 34 |
| index | caida | 2048 | 全新对抗 | 3 | zero | 43 | 43 | 34 |
| index | caida | 2048 | 全新对抗 | 4 | zero | 43 | 43 | 34 |
| fp64 | caida | 1024 | 全新对抗 | 0 | zero | 1312 | 1312 | 910 |
| fp64 | caida | 1024 | 全新对抗 | 1 | zero | 1312 | 1312 | 910 |
| fp64 | caida | 1024 | 全新对抗 | 2 | zero | 1312 | 1312 | 910 |
| fp64 | caida | 1024 | 全新对抗 | 3 | zero | 1312 | 1312 | 910 |
| fp64 | caida | 1024 | 全新对抗 | 4 | zero | 1312 | 1312 | 910 |
| fp64 | caida | 2048 | 全新对抗 | 0 | zero | 50 | 50 | 34 |
| fp64 | caida | 2048 | 全新对抗 | 1 | zero | 50 | 50 | 34 |
| fp64 | caida | 2048 | 全新对抗 | 2 | zero | 50 | 50 | 34 |
| fp64 | caida | 2048 | 全新对抗 | 3 | zero | 50 | 50 | 34 |
| fp64 | caida | 2048 | 全新对抗 | 4 | zero | 50 | 50 | 34 |

## Interpretation and boundaries

- This is a new selector, not the old predictive RA6-Z. BF candidates cannot be excluded by predicted top-five pruning. The guaranteed objective is min(learning FP of BF-replay winner, learning FP of repaired RA6), not min of unknowable future FP.
- Exact learning replay is paid for:13 BF candidates plus one learned-anchor replay, with original early stopping/no-cache shortcuts. Per-case timers include builds and replay, but this is not a new controlled timing/scalability campaign; model/scores are loaded and first-use JIT may contribute. No transfer of the old49.24× statistic-only speedup claim.
- Repaired RA6 and BF controls reproduce archived round17 configurations, full static flags, tail FP/hits, and BF training objectives. Their repaired statistic arrays are checked equal to the original on this fixed matrix. Historical predictive RA6-Z/expandedReplay values are retained only as explicitly labeled historical comparators.
- Each chosen candidate is actually evaluated after selection, and selected zero-tree paths receive full-tail native BF/CLOCK and populated-cache member checks. No model or features are required for zero-tree deployment; search still evaluates a learned model.
- FP ratios use+1 smoothing per case before medians. Same workloads/models recur; five fresh-adversarial seed labels can describe the same deterministic stream. No independent-sample significance claim, oracle gate or parameter retuning.
- External index cost and fp64 collision limitations remain. This does not provide a Direct/no-filter database candidate or prove latency improvement. Paper and prior frozen sources are unchanged.
- In the inspected original G-PLBF adaptive script, best_epoch=0 is initialization and the search lower bound is2; shared Gama prefixes start at1. No genuine zero-tree BF fallback exists in those inspected paths. This is not a statement about all possible Gama variants.

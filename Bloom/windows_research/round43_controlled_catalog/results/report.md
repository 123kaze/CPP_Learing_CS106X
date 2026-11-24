# Round43：受控目录条件实验（不是生产轨迹）

完整54case keys，378条主比较、162条固定配置控制、1296次真实本机SQLite查询窗口计时。按预设强度/关联/预算/seed完整执行，不按tail挑赢家。

## RA的完整FP对照

| 特征强度/关联 | vs BF 胜/平/负 | RA/BF平滑比中位 | vs Replay 胜/平/负 | RA/Replay比 |
| --- | --- | ---: | --- | ---: |
| a0/neutral | 0/0/9 | 1.196463 | 5/0/4 | 0.998663 |
| a0/high_hot | 0/0/9 | 1.119390 | 9/0/0 | 0.883782 |
| a0/low_hot | 1/0/8 | 1.118551 | 9/0/0 | 0.876257 |
| a6/neutral | 9/0/0 | 0.008737 | 7/1/1 | 0.936069 |
| a6/high_hot | 9/0/0 | 0.002457 | 6/0/3 | 0.916667 |
| a6/low_hot | 9/0/0 | 0.054726 | 8/0/1 | 0.789474 |

## 实际本机SQLite完整路径（RA vs BF+Cache）

| 强度/member目标比例 | 胜/负 | 配对耗时比中位 | 少查backend的设置数 |
| --- | --- | ---: | ---: |
| a0/p0.1 | 0/27 | 1.458712 | 2/27 |
| a0/p0.9 | 0/27 | 1.149998 | 1/27 |
| a6/p0.1 | 8/19 | 1.245794 | 27/27 |
| a6/p0.9 | 0/27 | 1.120621 | 27/27 |

## Interpretation and limits

The raw domain really is uint64. Full64-bit bijective hashes in cache are exact key representations, not generic compressed-string fingerprints. No member index, no probabilistic FN guarantee invoked. Input/source models/queries are synthetic and deliberately vary feature learnability and popularity correlation. Labels are not read by the online query path. All three correlation arms have identical regional traffic masses; only within-region rank concentration differs. Strong-model results do not establish that production workloads share that distribution.

Actual query timers include8byte decode, bijective hash, cache, top8feature extraction, model, packed BF, actualSQL and negative feedback. NoFilter avoids unused preprocessing. Warm local SQLite is not remote/productionKV. Two chosen member proportions are experimental parameters, not measured workload statistics. Fixed20000query windows are NOT the750000negative-query FP table. Queries/seed/budgets share catalogue inputs, so no independent-sample p-values are reported.

cost_crossovers.csv derives the EXTRA additive backend lookup cost at which measured query differences would cross, only if RA saves calls. cost_projections.csv values at0/5/20/100us are NOT timing measurements, not a discovered deployment and not an excuse to call an FP loss a win. Startup is separately accounted from model/score/tree/GT/selection/executable rebuild, with common input/DB/JIT outside; shared-label assumption is explicit. Long-run break-even requires stationary measured rates and does not validate dynamic rebuilds.

Fixed-config controls hold anchor trees/partition/cache/BFbits fixed and compare h/traffic/miss. Conditional AMGM is recorded only with its support/interiority conditions; actual CLOCK does not holdT exogenous, so failures do not falsify that restricted theorem. FullRA6 still changes partitions/configurations and is heuristic. ZGate learning-only selection is a labeled variant, not a future guarantee or free speedup.

All development and query feature support, AUC and bin-presence-rule results are in diagnostics/workerJSON. A generator branch knows which catalogue it is generating; no deployment decision may use that construction label. Reproducible by frozen code/seeds; no new real-workload claim, no manuscript modification.

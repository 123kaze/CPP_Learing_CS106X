# Round53 release index / 第53轮无索引实验发布索引

2026-11-24。用户确认实验完成后要求push。本次发布第53轮完整结果、失败版本、资源授权/工作区修复过程及核验材料；论文、旧标签、已删除的旧实验和无关文件不动。各轮“未自动发布”等状态句是运行/归档时点记录；实际发布以包含本索引的Git提交为准。

## Main result and limits

The fixed matrix is complete: **62 cases × 7 methods = 434 rows**, comprising 38 completed v2 cases reused byte-for-byte and 24 newly executed v4 cases. This is **not** a rerun of all 1,146 historical cases or the old end-to-end Table4. No new independent holdout or production deployment claim is made.

All methods use physically charged caches containing complete keys, with **zero required deployment member-verification-index bytes**. Integer keys are losslessly encoded in8 bytes, CAIDA-flow tuples in33 bytes, MAWI-flow tuples in9 bytes; URL/Shalla keys longer than128 bytes bypass the cache. Hash equality alone never establishes a cache hit. Static same-version membership and insertion only after exact negative confirmation remain required for the strict zero-FN semantics; this round uses offline reference replay, not a newly timed online backend.

| RA comparison | Wins / ties / losses | Median paired (FP_RA+1)/(FP_baseline+1) |
| --- | --- | ---: |
| Gama | 44 / 16 / 2 | 0.508825 |
| Gama+10% | 50 / 4 / 8 | 0.840374 |
| Replay | 35 / 5 / 22 | 0.997776 |
| RA-global | 28 / 18 / 16 | 1.000000 |
| BF+Exact | 59 / 2 / 1 | 0.050871 |
| PlainBF | 60 / 2 / 0 | 0.027503 |

**Retained counterexample:** CAIDA-flow16KiB has RA1,964,716 FP vs Replay881,822 and BF+Exact1,374,365. Across the related configurations, simple sums are RA7,722,362 vs Replay6,700,667; the sums are not one deployment workload, but prevent interpreting a favorable win count as universally lower FP.

Selection/build timings retain their implementation scope: paired Replay/RA median1.724× in the38 reused v2 cases and8.971× in the24 workspace-optimized v4 cases. The pooled4.354× mixes workspace versions, excludes retraining and service inference/backend latency, and is not an end-to-end speedup.

## 完整证据入口

- [最终报告](../windows_research/round53_index_free_recheck_v4/README.md) · [434行结果](../windows_research/round53_index_free_recheck_v4/results/main.csv)
- [完整覆盖与统计核验](../windows_research/round53_index_free_recheck_v4/results/verification.json)
- [38case复用来源与SHA](../windows_research/round53_index_free_recheck_v4/results/reuse_provenance.json)
- [工作区等价验证：4case/28行](../windows_research/round53_index_free_recheck_v4/results/workspace_equivalence.json)
- [14项单元测试](../windows_research/round53_index_free_recheck_v4/results/preflight_tests.log)
- [独立编码/算术核验](round53_evidence_20261124/verification.json)：166来源/输入文件hash、9份数据完整key反解身份及完整配对统计。项目内部交叉复算，不是第三方独立复现。
- [外层完整档案清单](round53_evidence_20261124/archive_manifest.json)：同时纳入原版及v2/v3/v4，保留各版本原清单。
- [逐阶段执行与授权记录](第53轮无索引重跑执行记录_20261124.md)

## 失败与修复，没有覆盖旧记录

1. [原版](../windows_research/round53_index_free_recheck/README.md)：CAIDA包含128bit地址，原uint32/9byte假设失败；未产生真实方法FP。
2. [v2](../windows_research/round53_index_free_recheck_v2/README.md)：无损地址修复，完成38case后触发4GiB RSS上限。
3. [v3](../windows_research/round53_index_free_recheck_v3/README.md)：用户授权6GiB，仍触发上限；没有新增完成case。
4. [v4](../windows_research/round53_index_free_recheck_v4/plan/design-freeze.md)：用户授权工作区优化，只释放候选中本轮后续不使用的逐查询`q_region`数组，保留实际region级路由metadata/计费及所有选择逻辑；先等价验证，再完成剩余24case。新worker峰值3,919,200,256B（3.65004GiB），pipeline783.044秒。两次内存中止记录原样保留。

Raw logs/keys used as datasets, prepared NPZs, model/data caches, JIT binaries and unrelated repository files are excluded. Verification that requires those local inputs must not be claimed complete in a data-free clone. The original UDP/TCP task construction, generated static workloads, previously used MAWI24, long-key bypass and unmeasured deployment costs remain limitations. **The manuscript is unchanged.**

# Round55 release index / 第55轮完整无索引主实验发布索引

2026-11-26。用户要求push。本次发布第55轮完整主FP矩阵、原版/v2/v3失败记录、v4成功结果、独立档案核验及研究表图；同时保存第54轮未运行草稿和第56轮串行计时冻结源码/协议。**第56轮结果/日志不属于本次快照**：发布准备期间收到72个正式worker完成、后台exit0的通知，但本次仍保持事前确定的code-only范围，未把尚未独立核验的计时结果混入发布。

论文、既有公开结果、用户删除的历史与旧标签不改。文档中“未push”等句子保留其当时状态；实际发布以包含本索引的Git提交为准。

## Full exact-key matrix / 全量范围

**1,146 historical main cases + 4 previously used MAWI24 cases = 1,150 fresh executions**, with 14 main method/phase rows per case (**16,100 rows**), 4,188 ablation rows, 11,500 top-10 candidate records and 41,666 full weighted-candidate records. All 34 dataset-budget settings are complete. Pilot results were not reused as formal results.

Complete keys are physically charged to the CLOCK cache; required member-verification-index storage is **0 bytes**. Key widths are8 bytes for integer IDs,33 for CAIDA-flow,9 for MAWI-flow, and128-byte slots for URL/Shalla with longer keys bypassed rather than truncated. Strict zero-FN semantics require static same-version membership and exact negative confirmation before insertion. This offline reference replay is not a production backend measurement.

## Results and limitations

On **1,076 non-probe main cases**, RA vs Replay is **414 wins / 186 ties / 476 losses**, median smoothed paired FP ratio **1.000000**. The reference≥30 subset has **745** cases (not the old748) and median **1.000384**. Setting totals, computed by averaging seeds within workloads before summing workloads, are no worse than Replay in21/30 settings and no worse than Gama in30/30.

The intended criterion is cheaper prediction-based selection with acceptable FP trade-offs, **not a requirement that RA have fewer FPs than exhaustive learning replay**. Replay minimizes learning-period FPs, not future-tail FPs, and RA changes segment weights outside Replay's candidate family. A median near1 is not proof of equivalence or non-inferiority.

Counterexamples remain visible:

- CAIDA-flow16KiB: RA1,964,716 vs Replay881,822 FPs.
- URL128KiB, uniform10k, seed4: RA754 vs Replay1; the difference is100.4FP per million evaluation queries.
- URL128KiB, Zipf1.2/100k, seed1: RA2,989 vs Replay234; this case remains in the≥30 subset.
- Probe replay is separate: URL256KiB, seed2 has RA155,529 vs Replay4.
- Learned Stacked beats learning-warmed RA in8/30 settings; the older prefix-cache claim does not transfer unchanged.

All four MAWI24 exact variants beat Replay here, but this is a **post-hoc recheck on previously used data**, not a new independent holdout. Dataset/protocol construction limitations remain; cases share models and pools and are not independent applications.

Two exact-adaptation gaps were diagnosed without changing the frozen run: the predictor omits the cost of non-cacheable long keys, and physically identical zero-capacity candidates can occupy the entire top-five shortlist. These are documented failures, not silently repaired measurements. See the diagnosis below.

## Evidence / 证据入口

- [完整结果与边界](round55_evidence_20261126/全量结果.md)
- [退化机制核对，尚未修复](round55_evidence_20261126/退化原因核对.md)
- [v4完成回执](../windows_research/round55_exact_full_main_v4/results/completion.json)
- [运行器核验与全部分组统计](../windows_research/round55_exact_full_main_v4/results/verification.json)
- [独立完整核验](round55_evidence_20261126/final_audit/verification.json)：40source、267input SHA在实验主机上全部验证；1150Gama、1146Stacked和62第53轮case回归。
- [逐case CSV](../windows_research/round55_exact_full_main_v4/results/cases.csv) · [全部方法行](../windows_research/round55_exact_full_main_v4/results/rows.csv)
- [最终研究表图v3](round55_evidence_20261126/final_artifacts_v3/README.md) · [PNG视觉检查](round55_evidence_20261126/final_artifacts_v3/visual_inspection.json)。13CSV、6PNG及PDF；初版/v2保留，CSV字节不变，仅改排版。PDF未独立渲染检查。
- [TODO](无索引主实验全量重跑_TODO_20261125.md) · [本地LaTeX label映射](无索引主实验_图表映射_20261125.md)
- [发布文件清单](round55_evidence_20261126/archive_manifest.json)

## Failure history / 失败保留

1. [原版](../windows_research/round55_exact_full_main/results/failure.json)：接错较早Learned Stacked入口，pilot断言失败，未进入formal。
2. [v2](../windows_research/round55_exact_full_main_v2/results/failure.json)：改接正确round6 baseline并加回归，完成5pilot后磁盘保护中止。
3. [v3](../windows_research/round55_exact_full_main_v3/results/pilot_gate.json)：补齐7pilot，但原8小时保守成本gate未过；失败没有改为通过。
4. [v4](../windows_research/round55_exact_full_main_v4/plan/design-freeze.md)：用户另授权原实现分批及2worker并行，放宽host RSS保护；不减案例、不优化回放，完成全部formal。

授权磁盘清理回执随档案保留，raw/压缩数据不发布。旧manifest要求已删raw的核验必须先恢复输入，不能虚称缺失输入已检查。

## Paused and in-progress work

- [第54轮](../windows_research/round54_review_suite/README.md)是暂停、未冻结、未正式运行的审查补充草稿，不构成科学结果。
- [第56轮选择计时](../windows_research/round56_exact_selection/plan/design-freeze.md)只发布冻结代码/协议；后台已报告72个formal worker完成，但尚待独立核验，结果及日志排除在此快照之外。此选择计时仅对应原full-pool实现，不能当作任意优化Replay的速度下界。
- Fresh-training construction, complete online query/backend paths, scalability, paperdata and TCP-only reruns remain unfinished. Round55 concurrent-process times must not replace uncontended timing results.

## Data-free archive verification

```bash
python3 -I docs/round55_evidence_20261126/archive55.py --verify
```

This checks the release manifest, archived cases, physical ledger arithmetic and exported rows using the standard library. Frozen inputs available in the clone are hashed; missing raw/prepared/model-cache inputs are explicitly listed as **not checked**, not fabricated as passed. The experiment-host full-input receipt remains a separate historical artifact. No copyrighted source PDFs, raw datasets, model caches, JIT files, manuscript changes or unrelated watchdog logs are included.

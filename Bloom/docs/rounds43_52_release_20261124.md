# Rounds 43–52 publication index / 第43–52轮发布索引

2026-11-24. This release preserves successful, negative, ineligible and failed-stage records, including explicit repair/resource-extension variants. It does not alter the manuscript, previous frozen sources, removed experiments or the `pvldb-submission` tag. Each archive's final SHA manifest was checked before publication. Raw logs, key blobs, offline databases, large downloaded archives and executable tools are excluded.

本次推送第43–52轮的完整证据。各轮README或执行笔记中的“未push”是归档时点的历史状态；本索引及各仓库包含它的Git提交记录对应本次发布，不应把旧状态句理解为当前远端缺少这些文件。原报告/代码/结果不为发布而重新生成。

## Main new result — and its limits

[Round52 complete result](../windows_research/round52_sis_filter_controls/README.md) compares a real-source SIS HTTP response task under two training recipes. The explicitly new `balanced_clip` recipe is shared by all learned baselines, not just RA:

| Comparison | Wins / ties / losses | Median paired smoothed FP ratio |
| --- | --- | ---: |
| RA vs BF+Exact128, original training | 8 / 0 / 1 | 0.692683 |
| RA vs Replay, original training | 5 / 0 / 4 | 0.982699 |
| RA vs BF+Exact128, balanced_clip | 9 / 0 / 0 | 0.055210 |
| RA vs Replay, balanced_clip | 7 / 0 / 2 | 0.882353 |

Selection-stage paired speedup over Replay: 3.797× original / 3.858× balanced_clip; all nine cases faster in each recipe. **This is not end-to-end service speedup.** Every filter budget and static-member/cache FN check passed, with no required member-verification index for Exact128.

**Do not hide the counterexample:** balanced_clip seed5002/1343KiB has RA312 FP vs Replay53. Across the nine related budget/seed cases, simple FP sums are RA846, Replay647, BF5791. The sum is not one deployment workload, but makes clear that 7/9 wins and a favorable paired median do not establish lower aggregate FP than Replay. Original training also retains its RA308 vs Replay45/BF56 failure.

SIS membership is a retrospective stable **observed HTTP success/404 target** task, not independently verified business-record existence. Data and training were explored before this matrix; it is **not a new independent holdout**. Natural mixed-stream inference/SQL time, startup amortization and independent-period/application confirmation remain unmeasured here. Low original negative-query share and seed5002's removal of a hot key by key-heldout splitting are disclosed. The manuscript is unchanged.

## Complete experiment map

| Round | Evidence / result | Interpretation |
| --- | --- | --- |
| [43](../windows_research/round43_controlled_catalog/README.md) | 378 main results, 162 controls, 1296 SQLite timing windows | Controlled synthetic exact-uint64 catalogue; strong/weak and unfavorable cases retained; not production evidence |
| [44](../windows_research/round44_trace_snapshot/README.md) / [report v2](../windows_research/round44_report_v2/README.md) | Three fixed Twitter samples; 147 results; RA vs BF1/20 | Real requests, constructed checkpoint-directory task; original report's duplicate-field failure preserved, report-only repair |
| [45](../windows_research/round45_namespace_diagnostics/README.md) | 36 development models, feature branch failed its predeclared gate | No new tail FP; reserved Twitter samples were not opened |
| [46](../windows_research/round46_dns_qualification/README.md) / [format v2](../windows_research/round46_dns_qualification_v2/README.md) | MACCDC DNS qualification: only18 positive names | Competition data, not production; failed header assumption and explicit mapping repair preserved; no filter comparison |
| [47](../windows_research/round47_sis_acquisition/README.md) / [acquisition v2](../windows_research/round47_sis_acquisition_v2/README.md) | Verified3GB public SIS archive; local prebuilt tool | Initial network resource gate failed; user-authorized extension recorded, no local compilation/global installation |
| [48 qualification](../windows_research/round48_sis_may_qualification/README.md) / [extraction v2](../windows_research/round48_sis_extract_v2/README.md) | Full May file verified; fixed2M-line prefix failed qualification | Initial extraction timeout/partial retained; larger resource limits explicitly authorized; no threshold change to declare prefix success |
| [49](../windows_research/round49_sis_inventory/README.md) | Complete41.7M-line inventory, exact old-prefix regression | Explicit post-prefix exploration, not an independent holdout; no method FP |
| [50](../windows_research/round50_sis_fullfile_diagnostics/README.md) | Full-file split qualifies; original training unstable | Data/workspace, skew and score saturation disclosed; no label or score reversal |
| [51](../windows_research/round51_training_stability/README.md) | Four fixed training recipes, 12 development models | Preselected balanced_clip gate passed; not a tail-performance selection |
| [52](../windows_research/round52_sis_filter_controls/README.md) | 126 main results, 54 fixed-configuration controls | Full original/new-recipe controls, byte accounting, FN checks and negative cases retained |

## Verification and planning records

- [Round43 independent arithmetic/hash audit](round43_evidence_20261123/verification.json)
- [Round44 prefix/split/report audit](round44_evidence_20261123/verification.json)
- [Rounds45–46 qualification audit](round45_46_evidence_20261123/verification.json)
- [Round48 fixed-prefix audit](round48_evidence_20261123/verification.json)
- [Round49 readonly inventory audit](round49_evidence_20261123/verification.json)
- [Rounds50–51 training audit](round50_51_evidence_20261124/verification.json)
- [Round52 complete matrix, sums and worst-case audit](round52_evidence_20261124/verification.json)
- [Exploratory search and verification log](探索搜索与独立验证计划_20261123.md)
- [SIS training and filter-comparison log](SIS训练与实体对照执行记录_20261124.md)

These are project-local checks and re-computations, **not third-party independent reproduction**. Tests, frozen sources, full results and failure logs are included. Some verification commands require the original private/local downloaded data or upstream setup files; missing inputs must not be reported as verified. Sources/licenses and data-construction limits are linked from the relevant round.

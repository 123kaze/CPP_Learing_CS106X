# 第55轮独立档案核验与exact表图工具

2026-11-26。此目录不属于已冻结round55执行代码；不改冻结代码、不改论文、不自动发布。**1150case已完成，独立完整核验通过。** [全量结果](全量结果.md)；最终表图采用[final_artifacts_v3](final_artifacts_v3/README.md)，[PNG视觉核验已通过](final_artifacts_v3/visual_inspection.json)。后续独立串行选择计时已另开第56轮，不与第55轮过程计时混用。

## 已做与未做

- `audit55.py`：标准库独立读档核验，不import实验模块，不重跑query。
- `partial_snapshot_01/`：889/1150case的不可覆盖部分快照，40source SHA通过，267input SHA延期。12446方法行、3246消融、8890top10、33301weighted候选记录。快照中的auditor SHA记录当时版本；随后增加了“应做第53轮回归的case不能缺标记”检查，未追改旧回执。
- `partial_snapshot_02/`：增加强制第53轮回归覆盖检查后重新核验，900case、12600方法行、3288消融、9000top10、33643weighted记录通过；40source SHA通过，267input SHA仍待最终核验。两份快照都保留，不把后一份追写进前一份。
- `test_audit55.py`：9项有效档案/故意破坏输入的开发测试通过。
- `final_audit/`：完整1150case独立核验通过，40source及267input SHA全部核验，无延期输入。
- `artifacts55.py`：Table2/3/7、预测表、Figure1/4/5对应的本地CSV/PNG/PDF生成器。要求完整独立audit通过才能运行，现已执行；最终输出`final_artifacts_v3/`，6张PNG检查通过。初版和v2及两份旧生成器源码保留；13份CSV各版相同，仅调整排版。PDF由相同figure生成，未单独PDF渲染核验。
- `test_artifacts55.py`：8项聚合和内存内图形渲染测试通过。合成fixture仅在内存或自动清理的临时目录，不作为实验结果保留。
- `palette_validation.json`：静态浅色图的配色机器验证回执。CVD/常规区分检查通过；橙/青色对比度WARN由CSV、文字及形状/分面补足。没有暗色网页或交互图交付。

## 在Bloom目录执行

开发测试：

```bash
.condaenv/bin/python -I docs/round55_evidence_20261126/test_audit55.py
.condaenv/bin/python -I docs/round55_evidence_20261126/test_artifacts55.py
```

最终核验和图表生成已经执行。下面是命令模板；已有输出目录不可覆盖，复现时把`--out`换成新的目录名。前提是round55 v4的completion.json存在且status=complete，完整输入均可读：

```bash
.condaenv/bin/python -I docs/round55_evidence_20261126/audit55.py \
  --round windows_research/round55_exact_full_main_v4 \
  --out docs/round55_evidence_20261126/final_audit

.condaenv/bin/python -I docs/round55_evidence_20261126/artifacts55.py \
  --round windows_research/round55_exact_full_main_v4 \
  --audit docs/round55_evidence_20261126/final_audit \
  --out docs/round55_evidence_20261126/final_artifacts
```

所有输出目录必须不存在；不覆盖失败、旧核验或已生成表图。若发现错误，保留失败回执，修后用新输出目录。最后需Read每张PNG检查标签/范围/布局，再记录视觉核验，不能把unit test或生成成功当作视觉核验。

## 冻结的范围约束

- 1146主case＝1076非probe＋70probe；MAWI24四例是已用数据的事后exact变体。无formal结果复用。
- Table2总量：每workload先seed平均再sum；不把低FP删掉。
- Table3：hindsight（seed0–2）否则Replay作reference，≥30子集与完整1076并列。新数量由新数据计算。
- 消融：先seed0–2均值再加1平滑作比。原`round5_dp/src/report5.py:e6`输入未排probe，因此同时提供`original_main_including_probe`、`main_nonprobe`、`probe`，不隐性选分组。MAWI24单列。
- 预测表：静态seed1–4、不含probe，前10实测最优≥30或<30分列；前5内相关性、择优命中和候选相对误差按原`e3_independent.py`定义。常数相关性未定义需记数量，不能补0或1。
- Figure1原图脚本位于`paper/figures/src/motivation/plot.py`，不是`paper/vldb/figures/src/motivation/plot.py`。已只读核对五负载和右图三Shalla＋CAIDA-flow/MAWI21范围；exact版本保持范围，改为小多图而非叠七色。
- Figure4保留全部点，不复用旧图0.45–2.3横轴范围裁掉异常点。
- Figure5拆分图原范围16/24/32KiB；预测图包含128。新CSV给全四预算，metadata与array header分账，不藏未用预算；内存与FP各用独立面板，不用双轴。

## 不能由本目录证明的事项

档案审计核对记录与选择逻辑的一致性，不是重新训练/打分/重放全部queries；Replay学习记录不保存est_fpr，不能独立重建完全相等FP时的第二级tie-break。它不把静态cache零FN前提推广到动态成员集，不把offline标签反馈推广成生产backend。

当前parallel批次时间不替代独占选择、完整construction、query或scalability计时；这些还需后续新实验。paperdata/TCP-only等独立矩阵也不由1150case自动覆盖。论文未修改。

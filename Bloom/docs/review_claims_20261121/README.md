# 性能表述修订：待审阅补丁（未应用）

2026-11-21生成的待审阅补丁快照。最初用户选择“只生成待审阅补丁”。2026-11-22后续曾按“实施所有”修改本地论文的实验章节；用户随后要求**不再改论文、也不恢复**，因此保留该局部改动，仅继续实验/MD。四文件补丁没有整体应用，论文仓库不在本次实验发布范围内。

- [补丁](performance-claims.patch)
- [生成脚本](build_patch.py)：只读取论文仓库、只在本目录写补丁，没有apply功能。
- [文件与补丁hash核验](verification.json)

## 基准与范围

基于 `paper.git` 提交 `e25665872d6f4f00026883f9a5be492bc8a8c9ad`，只涉及：

1. `vldb/sections/abstract.tex`
2. `vldb/sections/introduction.tex`
3. `vldb/sections/experiments.tex`
4. `vldb/sections/conclusion.tex`

共13处精确文字替换，无算法修改，无表格数据重选，无MAWI-24留出结果替换。

## 修订内容

- 将笼统的“matches or beats Replay”改成**相近的观测FP与较低选择成本**，不声称统计等效、非劣或普遍优越。
- 保留21簇原双侧Wilcoxon `p=0.096`，新增按8个完整数据集、50000次bootstrap、seed2901的分析说明。修复后效应0.9751，95%区间 `[0.9473,1.0012]`，明确跨过1、小簇和事后分析边界。
- 将候选选择效率与部分工作负载的重加权FP改善分为两项结果，不把选择加速等同于端到端查询加速。
- 明确11倍左右来自全部748有效案例，不能误写为仅重复子集的中位数。
- 将“931MB trace”改成“931MB learning state, including800MB raw trace”。
- 如实将SQLite旧实验描述为先按已知标签批量模拟Filter/Cache、再执行真实SQL的计时，**不伪称在线交错实验已完成**；纠正CAIDA/COD的NoFilter比较。
- 敏感性严格不高于Replay由14/16改为13/16。

## 数字来源

- [Round29v2统计与资源审计](../../windows_research/round29_evidence_audit_v2/results/summary.json)
- [Round30原始数字复算](../../windows_research/round30_submission_audit/results/numeric_audit.json)
- [Round30解释与仍未解决的问题](../../windows_research/round30_submission_audit/README.md)

## 已核验／未做

- [x] 四个源文件逐段唯一匹配，13处替换完成。
- [x] TeX大括号和环境计数静态检查通过。
- [x] `git apply --check` 在基准版本上通过；该命令只检查，**没有应用补丁**。
- [x] 生成补丁并执行只读检查时没有改论文；用户作者信息、已删除内容与算法源未改。
- [ ] 四文件补丁整体应用：未进行。后续只在本地实验章节写入了部分更新，按用户最新要求保留，不继续编辑或恢复。
- [ ] 完整稿件审核及修订：已暂缓，后续仅写MD。
- [ ] 编译／PDF更新／版面检查（本轮未运行本地TeX编译器）。
- [ ] 提交或push。

**后续进展（2026-11-22）：** [第31轮](../../windows_research/round31_sqlite_online/README.md)已完成真正交错SQLite重测，共312条计时。这个补丁是在重测之前生成的审阅快照，其中“在线实验尚未完成”的句子已过时；正式应用前应结合第31轮结果刷新版本，不能直接当最新定稿。原补丁保留，未自动重写或应用。

**其余开放项：** Proposition5.2的严格保证与具体反例、GT归一化消融等不由这份文字补丁解决。论文更新项不能因为补丁存在就打勾。

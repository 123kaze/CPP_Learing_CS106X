# 第55轮v2：修正Learned Stacked基线接入，完整矩阵不变

2026-11-25。继承[原第55轮完整协议](../../round55_exact_full_main/plan/design-freeze.md)的1146＋4case、原seed/workload/预算、10cold＋3warm＋1stacked、消融/排名/hindsight/加权全候选诊断和全部资源限制。原源码、freeze和失败记录保留。

## 失败原因及明确修复

原版15fixture通过；URL64KiB全部3pilot完成（约134.5秒、峰值0.948GiB），CAIDA128KiB完成第1个uniform-all case（385.222秒），随后Learned Stacked非None/预算联合断言失败；worker峰值2458091520B，非内存失败。

代码核对发现原版错误导入`round2_backlog/src/learned_stacked.py:choose`；本地论文Table`tab:main`实际来源是`round6_bucket/src/stacked_full.py:stacked_fp`及`e7_extra.py`。后者使用共享DP引擎，学习选择与全学习部署的side layers不再可行时明确回退原Gama。原较早版本可返回None，且其基础分配器/份额搜索和论文主表不一致。

v2改用**原第6轮冻结stacked_fp**，按原6个side份额用E5.build建立bases，并复用它的完整选择/FN检查/回退；不临时为本轮发明新tie-break或调弱baseline。新fixture强制half-learning可行但full-learning不可行，断言恰好回退Gama。同时原1146个LearnedStacked历史FP进入新case清单与冻结输入，要求每case新运行FP逐项回归；MAWI24无同一旧表时仅新检查预算/FN，不伪造旧回归。

其余10主方法、3warm、GT19、exact cache、消融、候选排序/诊断完全不改。原URL三例与CAIDA一例结果都保留为失败版pilot，**不并入新正式矩阵**。新版本重跑原7个固定pilot，不换seed/工作负载。

## 资源和成本边界

16测试通过后另冻新SHA；单worker4GiB、磁盘保留4GiB、worker7200秒、formal28800秒、输出1GiB保持。原CAIDA385秒包含h权重hindsight回放141.912秒及162个RA加权候选全tail诊断，不能当成仅10个主方法的成本，也不能当所有seed都会相同。

原保守pilot外推可能高于8小时；新7例完成后按原闸门计算，超出则停止并向用户报告/申请分批时间，而非自动减case、丢诊断或扩大时间。尚未证明成本可在8小时内完成。

这不是内存失败重启，也不扩大已登记资源限制；只修正基线接错来源。论文和旧实验档案未修改，不自动push。

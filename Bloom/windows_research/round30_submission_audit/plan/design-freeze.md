# Round30：审查问题的只读核验

2026-11-21。参考论文 `paper.git origin/main e256658:vldb/sections/`；发布标签`ra-gama/pvldb-submission=3694ac9`。不修改论文、原算法或冻结轮次。

1. 从原始e789 JSON列出COD/CAIDA全部方法的文件／内存SQLite分解计时。对照执行顺序：批量`exe.run(mode2)`用成员标签更新缓存，再对accept列表执行SQL。不能冒充严格交错反馈计时；计数正确性不能仅据此否定。
2. 从e10.json按整数FP严格比较16个learning_share点；不看四舍五入比值。
3. 从round15v2 timing_rows.csv分开trace bytes、learning-state bytes与RSS。
4. 固定round19原748纳入口径重算全体／638重复子集的RA/Gama中位数和倒数，不替换成更有利口径。
5. GT19函数真实运行`a,b,b`，确认seen+unseen质量；不归一化、不替换算法。
6. Algorithm1：确认构建权重w与DP新epsilon下重新计算的miss vector是否一致于实际代码；只给文字修正建议。
7. Proposition5.2反例搜索：使用新round27两个月NASA缓存数据及其既定2701/2702/2703训练split，重新训练同参数200树（无新调参），把真实学习prefix中的distinct keys各查询一次，H保留对应尾段长度。按月份、seed、4/8/16KiB顺序检查原Gama和GT19-RA6完整候选选择；至首个结构/配置差异停止，保存已搜索设置、模型hash、候选评分、两结构全池flags等证据。若18设置都未发现，报告有限搜索未找到，不把评分表达式不同直接升级为已验证全称反例。新数据的反例不代表原140案例失效。

审查是反例/实现一致性核验，不是尾段优化算法。所有正式对比沿用固定代码，输出归档只写新目录；反例搜索不使用尾段FP挑选模型或修复规则。

# 第53轮v2：完整128bit地址编码修复，实验矩阵不变

2026-11-24。本轮继承[原冻结计划](../../round53_index_free_recheck/plan/design-freeze.md)的62case、7方法、434行、预算/模型/split/时序/seed/计时/资源上限与报告边界。旧版源码/冻结/失败日志保留，不覆盖。不是内存失败后的重启，也不是为了改善FP修改布局。

## 已观察的失败及修复依据

原版11测试通过，URL原始key对齐通过；CAIDA-flow原始字段核验在`dtype.kind in 'iu'`处停止。尚未运行任何真实方法pilot或看到本轮FP。

进一步完整字段审计（只读、只输出聚合类型统计，5.340452秒）：

| 原CSV | 行数 | 地址最大位数 | 非整数 / 非规范十进制 / 超uint128范围 |
| --- | ---: | ---: | --- |
| CAIDA | 8493974 | 128 | 0 / 0 / 0 |
| MAWI2020 | 7310243 | 32 | 0 / 0 / 0 |
| MAWI2021 | 4871259 | 32 | 0 / 0 / 0 |
| MAWI2022 | 4745391 | 32 | 0 / 0 / 0 |
| MAWI2024 | 3165739 | 32 | 0 / 0 / 0 |

CAIDA含128bit地址，所以旧9byte计划不成立。v2只修这个无损编码前提：

- CAIDA-flow：Source uint128 + Destination uint128 + Label uint8，固定33bytes；所有CAIDA-flow key同宽，不按成员/negative/FP选择。
- 四份MAWI-flow：保持原uint32+uint32+uint8，共9bytes。
- COD/CAIDA数值key仍为8bytes；URL/Shalla仍为Exact128，>128bytes绕过。
- 流地址按原始字符串读取，要求`str(int(text)) == text`且整数在所声明宽度范围内，然后转little-endian完整bytes。禁止float转换、截断、hash替代完整key或默默绕过宽地址。
- 每个raw tuple仍须与旧pandas hash、旧key次序和成员标签逐项一致；同hash不同raw tuple必须失败。

原所有选择算法、13 shares、4-way CLOCK、实占预算、62case/7方法、cold-tail、GT19、完整负结果和原Gama回归检查均不变。

## 额外预冻结检查

12测试：原11项覆盖加128bit无损回读、32bit溢出拒绝、非规范文本拒绝；布局和碰撞测试同时覆盖W=33。原失败不是完成实验；新结果在全新目录产生，不拼接或覆盖旧输出。

资源与停止规则沿用原计划：单worker/native1，RSS<4GiB、磁盘留8GiB、worker1800秒、正式矩阵7200秒；两pilot的粗略资源投影通过后才进入正式矩阵。失败不自动重试同一版本；若发生内存超限，不擅自重启或扩大内存上限。

论文不动、不自动发布；MAWI24不称新holdout；62case不冒充1146case全部重跑或旧Table4端到端重测。

# Round33：Good–Turing总质量归一化消融

2026-11-22。新变体／事后诊断；不修改GT19、RA6、原140无重复结果或MAWI24冻结留出。只改实验和MD，不改论文。第27–31轮已先推送。

## 三个固定估计器

令GT19已见有效率为lambda_x，u=N1/L，R=sum(lambda)，Z=R+u。

1. `GT19`：原样保留，作为冻结RA6控制；完全使用原population与bucket_prediction函数。
2. `SeenNormalize`：保持u，令lambda'_x=lambda_x*(1-u)/R。若R=0,u=1，则保持全零率与u=1；其他R=0情况拒绝。该方案把已见质量定为1-u。
3. `TotalNormalize`：lambda'_x=lambda_x/Z，u'=u/Z。

两种归一化都满足sum(lambda')+u'=1（数值容差）；不是SGT，不拟合新参数、不平滑缺档、不声称无偏。若新率向量的字节与未见质量都完全未变，则直接委托原预测函数，避免等价公式的运算次序引入无意义舍入差异。候选表通过透明观察包装器取回原函数返回的同一对象；不再多跑一遍DP，排名/哈希序列化在选择计时之外单列。保持原L/N1/counts整数语义，新增独立unseen_mass字段，不能通过改N1或L伪装归一化。Stage1 population和Stage2 bucket refinement必须同时使用新的未见质量。通过本轮独立函数与可逆runtime上下文适配，冻结源文件字节不动；GT19控制走原函数，退出/异常恢复所有绑定。

## 固定案例矩阵（30case keys，两种缓存，三种估计）

- 第18轮已确认受GT缺档影响的14个原案例：全部纳入，不再挑更有利者；具体键来自已冻结affected_cases.json。
- 4个真实UDP/TCP轨迹：CAIDA-flow、MAWI2020/2021/2022-flow，24KiB，seed0。
- 4个TCP-only：CAIDA32、MAWI2020 64、MAWI2021 41、MAWI2022 64KiB，seed0。
- 8个无重复控制：COD1024、URL128、CAIDA256、Shalla1024KiB，各每key一次与全新对抗，seed0。

共30×2cache formats(index/fp64)×3arms=180选择/构建/尾段评估记录。GT19控制必须复现round19合并档案中的同格式FP，避免把实现差异误认为归一化效果。每个case统一原25%learning与75%tail，cold cache，模型/树网格/缓存网格/DP/top5不变；不增加NR32或zero-tree门控。

## 输出与验证

记录原/新已见质量、未见质量、总质量、倍率、数组hash；候选表的完整树数/缓存份额/预测FP/排名和top5重叠；最终结构、packedBF/full-pool flags/hash、预算、全成员BF与最终Cache FN；尾段FP/hits/insert/eviction/bypass；计数、归一化、候选表、top5构建精排、尾段回放全部计时。通过额外候选表收集记录排名时单列诊断时间，不假称这是原选择器原生免费输出。重建payload与当前flags一致。

原和变体都实际评估，不能以预测改善代替实测改善；所有180行保留，无>=30过滤、无基于尾段的winner选择。+1比值按case配对，统计为描述而非独立样本显著性证明。无重复两变体必须与原GT19选择的结构实际逐字节一致，而非假设与Gama一定相同；该区别与NR32分开。

单测：a,b,b的两种归一化结果；all-singletons位级不变；unit-mass与概率边界；原L/N1/counts保持；pop/bucket语义与scoped hook异常恢复；独立新变量不能改变GT19控制的原函数路径。正式执行前冻结，fresh worker按dataset/cache顺序单线程，保留失败、不自动重启内存压力任务。

## 解释约束

这是判断归一化是否改变预测排序、配置和实测FP的限定消融，不能把较好的一个估计器事后替换原主方法或把MAWI24重新命名为独立留出。无论结果如何，都承认原GT19有效到达率并非规范化概率分布。

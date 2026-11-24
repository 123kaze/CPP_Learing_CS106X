# 第53轮：旧主任务的无成员索引、完整 key 缓存重跑

2026-11-24。响应用户“删掉索引重跑／做一轮新实验”。保留旧主表和前缀缓存证据；不编辑任何旧冻结源码，不修改论文，不自动 commit/push。

## 目的与本轮范围（实现/运行前登记）

直接检查：去掉前缀缓存依赖的成员验证索引，改用完整原始 key 的精确 CLOCK，在相同物理 Filter Budget 下，RA 相对 Replay、Gama、RA-global 和 BF+Cache 的结果如何。

本轮先做**固定62个case、7方法、434行**，不是宣称重新执行全部1146个case或旧论文Table4：

- 静态 COD / CAIDA / Shalla / URL：旧主表的全部预算（3/4/4/3个），每预算固定 `每key一次`、`uniform-全部`、`zipf1.0-全部`，seed=0，共42case。uniform/Zipf仍为10000000条，once仍使用原完整查询池。它们是原数据驱动的合成查询，不称真实时序。
- 原 CAIDA-flow、MAWI2020/2021/2022-flow：每数据原4预算、原完整负查询时序和25%/75%划分，共16case。
- MAWI2024-flow：原4预算，共4case。它已被使用；本轮只是旧留出数据上的事后缓存变体复核，**不是新独立holdout**。
- 不按FP、胜负或AUC改变上述数据、预算、seed、查询数、tail、缓存key宽度、方法；不删除高预算低计数或负结果。
- 本轮范围不包含额外seed、所有pool/Zipf指数、fresh/probe、TCP-only、SIS新训练或端到端数据库计时。结论不能覆盖这些未跑项。

## 无索引不是简单删除安全检查

用新的第53轮缓存实现复用第41轮完整key比较语义：一个owning uint8数组，32B头，每slot为 `W key bytes + uint16 length + valid byte + ref byte`，4-way CLOCK，1 byte/bucket hand，另计NumPy数组头。Hash只选bucket；命中必须长度和完整bytes一致。不借助成员索引、外部key字典指针或fp64概率界。

宽度由**key schema**事先固定，而非按结果选择：

- COD objID、CAIDA原No.整数key：无损uint64 little-endian，W=8。
- flow key：原CSV的 Source uint32、Destination uint32、Label uint8，无损9bytes，W=9。须逐项校验这些原字段的整数范围、成员标签、旧pandas字符串hash和原key次序，不能从float32特征反推地址。保留原协议任务的构造局限，不把该任务声称为模型非协议价值证据。
- URL/Shalla：旧parser得到的完整Unicode字符串以UTF-8编码，W=128；超过128bytes键绕过cache，不截断、不另存字典。报告长key和长key请求数量。原RA预测未建模长key不可缓存，本轮保持这一算法限制，不用tail修模型。

新loader直接读取已准备的ids/y/scores/model，只复用旧split，不调用会构建member_hashes/cache_cost/safe的旧Setup/load路径。运行时用禁止调用检查拦截这些入口；必需额外成员验证索引=0。BF构建仍合法读取成员hash输入，这不是部署时验证索引。

## 算法与公平性

7方法：Gama（无cache）、Gama+10%（沿用Gama树数）、Replay、RA-global、RA-PLBF-GT19、BF+Exact、PlainBF。

- 固定原200tree模型及14个树前缀，不重新训练、不换特征；所有learned方法共用相同已有分数。
- 原1000segments/5regions DP、13 cache shares、RA6 top5、GT19统计修复及tie-break均保留。
- 按新布局重新计算每个cache share的实占/slots，再重新选择，绝不直接给旧winner去掉索引后计作新结果。
- Replay对全部可行候选在learning期精确回放；允许旧规则的仅FP超best才提前停止。所有query均访问cache，包括static reject。
- 与旧主表一致：learning选择后，tail从空cache开始；不是warm-cache累计差分。
- Filter Budget包括模型payload、BF、路由、数组/字典头及完整cache实占。raw输入key blob/offsets、成员BF构建输入、分数数组、learning状态、进程RSS单列，不伪称总RSS相等。
- Exact cache的零FN依据是静态同版本集合与后端确认negative后插入；本轮为离线标签参考回放，不冒充逐query后端反馈计时。动态成员仍需失效协议。

## 核验与计时

1. 先单测布局预算/碰撞下全key比较/长keybypass/CLOCK状态/空cache/截断回放tie语义及故意调用索引入口失败。
2. 重建原始key，逐项对齐旧ids/y，冻结源码和全部读取输入hash。原data/scores/模型不改写。
3. 固定资源pilot：URL64KiB的上述三个workload，以及CAIDA-flow16KiB。pilot输出不用于筛选方法/数据或胜负；正式对应输出须逐项复现非计时字段。
4. 单worker、native threads=1；父进程监控RSS<4GiB、空闲磁盘>=8GiB。每worker最多1800秒、正式矩阵最多7200秒；超限停止并保留失败，不自动重启/换小数据或减少网格。
5. 各阶段记录实际耗时：rawkey准备、缓存模型/分数读取、公共tree统计、JIT、候选构建、learning统计、选择/回放、tail模拟、全member检查和wall/RSS。旧训练/打分作为复用输入，明确“本轮未重新计时”，不是填0声称免费。
6. 每实体BF断言全member通过；每最终cache对全member完整rawkey检查0命中，检查前后state SHA不变。对碰撞与member插入的单测确认negative-only流可以保持精确cache状态，但本轮不据此声称测了自然混合延迟。
7. 报告完整434行、逐case配对FP及+1平滑比、绝对计数、胜平负、最大退化和相应字节账。旧前缀结果只标为历史参照，不用不配对中位数比替代配对。

## 完成判据与边界

完成必须实际覆盖固定62case及全部方法，并通过输入/冻结hash、budget、FN、pilot、Gama无cache旧FP回归。失败/中止时只报告完成子集，不盖全轮完成章。

这是新无索引表示的事后鲁棒性实验，不删除旧结果，不把本轮当新的独立应用、不声称严格优于Replay或端到端更快。即使FP改善，系统总成本和原真实任务语义局限仍需单独验证。

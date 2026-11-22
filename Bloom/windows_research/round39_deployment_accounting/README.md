# Round39：学习期增量成本与回本边界（已完成）

**42设置、126个成本差分、168行资源明细及756个显式参数外推全部核验；五项单测通过。** 30个worker顺序完成，90.24秒。参数外推不是新的数据库实测。

[完整报告](results/report.md) · [调用差分](results/call_accounting.csv) · [资源表](results/resources.csv) · [学习状态](results/learning_state.csv) · [假设参数外推](results/scenario_projections.csv) · [核验](results/verification.json)

## 新结果：不能只看部署后的FP

| 对照情境 | index：学习＋当前尾段净减少调用 | fp64：学习＋当前尾段净减少调用 |
| --- | ---: | ---: |
| RA新在线采集 vs 已部署Plain BF | 10/21 | 9/21 |
| RA新在线采集 vs 已部署BF＋固定10%热Cache | 0/21 | 0/21 |
| 两者共享标签，再与学习选份额的BF+Cache一起冷部署 | 11/21 | 10/21 |

第二行在当前窗口内全部净增加调用，即使其中各10例的部署后尾段FP更少。它针对“学习时强制所有查询访问backend”的原协议与已部署baseline，不证明所有在线学习方案都必然如此，也不是实测端到端时间结论。

### MAWI2021-flow，24KiB，index的具体差分

学习857343个negative请求，尾段2572031个negative请求，RA尾段FP10347。

| baseline | 学习阶段baseline调用 | RA额外学习调用 | 尾段节省调用 | 学习＋尾段净节省 |
| --- | ---: | ---: | ---: | ---: |
| 已部署Plain BF | 270172 | 587171 | 608853 | 21682 |
| 已部署BF＋固定10%缓存（状态延续） | 10334 | 847009 | 27244 | -819765 |
| 共享标签后的学习选份额BF+Cache（cold） | 857343（共同采集） | 0 | 27313 | 27313 |

这里始终使用同一个baseline的学习与尾段计数，不能拿Gama尾段节省与Plain BF学习成本拼接。成员查询在两者无FN、成员集合一致的条件下抵消；不是把全部学习流都算作RA额外访问。

## 回本条件

`ΔT(N)=A+ΔL*C/1e6+N*[d-(1-p)*s*C]/1e6`。

- ΔL：额外学习后端调用；s：每negative query节省的调用数。
- A：新增非lookup启动、学习统计、训练、索引与重配置净成本。
- C：单次基本backend lookup/交互微秒；d：每总查询额外非lookup处理微秒，含模型、特征、cache及prefix验证差额。
- p：未来成员查询比例；本轮给定参数是说明性假设，不是新测得的生产配置。

只有`(1-p)*s*C>d`才有正的持续收益斜率；否则增加N不能摊销非负启动成本。A=d=0时，学习访问与尾段节省同时乘C，单纯使backend更慢不会改变按调用数算出的回本窗口。周期性重建时还必须重复计入A和ΔL，不能把一次启动无限期摊销。

## 资源与正确性

MAWI21该RA配置Filter实占24163B，另需索引323400B（含header），已知两项合计347563B，仍不含完整backend数据库、OS缓存或harness。

只在index且cache非空时需要验证索引；纯BF不需要。后端已有完整兼容索引时可以零增量复用，但不是索引没有成本。原始key有序也不意味着hash-prefix索引免费。

一般原始key域的fp64不是严格zero-FN替代。**还必须阅读[第40轮概率前提勘误](../round40_fingerprint_assumptions/results/report.md)：共享BF/cache哈希并按BF放行筛选cache条目时，S/2^64不能仅由“理想非恶意哈希”直接推出。** 本批有限fingerprint集合无交集，实际成员检查结果不变；exact uint64 key＋双射编码是不同的精确key缓存特例。

## 学习状态也有负面边界

原GT19的`state_bytes`仅含keys/counts的16D；加rates后三数组payload为24D。相对8L轨迹：本批15个不同dataset/seed输入中，2个的16D更大，3个的24D更大。

- MAWI20 TCP-only：D/L≈0.716，16D/8L≈1.433，24D/8L≈2.149。
- MAWI21 TCP-only：D/L≈0.632，对应1.264、1.897。
- MAWI22 TCP-only：D/L≈0.421，24D/8L≈1.264。

这些是payload比较，不是完整header/中间量/RSS峰值。不能将100M高重复实验的状态优势外推到高基数或低重复流。

## 没有冒充完成的部分

- 42个固定10% warm-cache控制、18个ClarkNet纯BF计数、18个ClarkNet学习选cache结果为新执行；其余明确复用已核验档案。
- 不宣称完整在线学习、特征提取、并发、真实远程数据库或重配置总时间已测量。
- “用已有严格zero-FN filter的拒绝证书采集negative标签”可能避免额外backend访问，但仍需完整入口日志和统计成本；本轮未实现该新协议，不能追认给旧结果。
- 论文、冻结旧代码和旧投稿标签未动。

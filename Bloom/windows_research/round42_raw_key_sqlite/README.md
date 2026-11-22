# Round42：原始key完整查询路径与SQLite成本（已完成）

[协议](plan/design-freeze.md) · [完整报告](results/report.md) · [189条查询计时](results/timings.csv) · [资源/延迟](results/resources_and_latency.csv) · [学习采集](results/learning.csv) · [条件回本](results/break_even.csv)

7项单测通过，7条pilot通过只看资源/时长的门限；正式3个worker顺序完成。含pilot/核验/报告全轮304.16秒；正式worker合计293.64秒。没有人工等待、没有本地C++构建、没有访问外部数据库。

**资源勘误必须同时阅读：[Round42资源账本v2](../round42_resource_ledger_v2/README.md)。** 冻结worker的`preparation.feature_matrix_bytes=128`实际只是NumPy视图头，漏掉3153200B payload；完整保留的视图＋owning base为3153440B。该字段不是Filter Budget。v2修正独立输入空间表，63行原FP/Filter/计时列逐字符串不变；旧代码/JSON不静默覆盖。

## 实测结果

自然顺序中成员比例为98.3845%–98.5255%，未重采样。原始HTTP key驱动本机SQLite精确BLOB GET，固定32bytes value、单连接、warm local DB。每seed固定前200000条eligible mixed-tail请求、3预算×7方法×3重复=189条。

- RA6-Exact128相对BF+Exact128：**0胜9负**，配对耗时比中位数**1.806769**。
- 相对Plain BF：0胜9负，1.881679；相对NoFilter：0胜9负，2.677098。
- 同等索引辅助预算下的PlainBF和DirectHashIndex均0FP，但仍慢于廉价本机NoFilter。减少FP并不自动减少总时间。
- 27个RA-Exact对三种baseline的观测速率/启动差分均无持续回本斜率；不伪造有限回本点。

16KiB组三seed的case中位数：NoFilter3.624us、BF+Exact5.450us、RA-Exact9.717us、prefix RA9.694us。这是每窗口wall/N，不是individual p50/p99；各方法中位数之比不是配对比。

### 代表性全账本：seed3601，16KiB，200000请求

| 方法 | 计入的train-to-ready秒 | 查询窗口秒 | Filter bytes | 额外index bytes | FP |
| --- | ---: | ---: | ---: | ---: | ---: |
| BF+Exact128 | 0.035386 | 1.090059 | 16377 | 0 | 198 |
| RA6-Exact128 | 1.964975 | 1.944265 | 15797 | 0 | 225 |
| RA6-prefix | 1.997649 | 1.929143 | 15487 | 260760 | 128 |

公共SQLite建库0.032206秒、文件2981888B另列；源日志重建来自第41轮14.04秒，准备输入加载/JIT/验证/全部pool工作区另列。这是可复现实验管线分项账本，不把离线pool评分写成最优在线实现，也不把RSS说成Filter Budget。

查询计时实际包含raw SHA256/mix、cache查找、按需词法特征、模型、BF、SQL、safe-prefix验证和反馈插入。NoFilter不做无用hash/特征。prefix索引在本地SQLite适配进程，**不是第35轮的远端进程placement**。

## 标签采集协议的新原型

seed3601原完整eligible learning窗口773833请求，三次重复：

- 强制全SQL：773833次lookup。
- 已部署固定10% BF+Exact128，无计数：762669次。
- 同一BF，用严格拒绝/精确cache命中作negative证书并记录完整入口计数：仍762669次。

三者每条收集到的成员标签完全相同；认证方案相对同一个现成BF增加**0次lookup**，避免强制全SQL多出的11164次。负key计数的Python对象账本230394B，未塞入Filter Budget。完整入口包括被拒绝的请求，不是只读经过筛选的backend日志。

有计数/无计数wall中位4.170/4.220秒的微小逆向差异含计时噪声，不能宣称计数让系统加速或CPU开销为零；相对NoFilter2.741秒仍更慢。此原型只验证同版本静态标签采集，不是并发训练、动态更新或原子重配置协议。

## 正确性与独立复核

所有真实SQL返回、放行mask、找到member的mask和最终cache逐字节匹配独立label-reference；0FN。额外[只读复核](../../docs/review_evidence_20261123/round42_final_cache_verification.json)重建63个最终缓存，匹配全部189条mask/cache SHA，对全部32581个member核查最终cache0命中；没有重跑SQL计时或改旧结果。

## 仍未完成的证据

数据仍来自1995年ClarkNet的回溯稳定子集；它不是新现代生产KV workload。无跨机器、并发、冷盘、动态成员/版本切换或第三方独立运行证明。3seed×3预算不是9个独立真实应用。实验明确支持“这个场景不值得部署学习模型”，而不是通过换窗口追求正结果。论文和旧投稿标签未动。

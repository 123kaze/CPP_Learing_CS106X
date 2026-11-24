# 第53轮原版：原始地址编码资格失败

2026-11-24。11项缓存单测通过，URL完整key重建通过；CAIDA-flow的原始key准备在整数dtype断言处停止。**没有运行真实方法pilot或产生FP矩阵。**

原因：原设计把所有flow地址视作uint32，但CAIDA包含128bit地址，不能无损用9byte `(src32,dst32,label8)` 编码。后续全文件只读字段审计确认CAIDA最大128bit，四份MAWI最大32bit；所有地址均是规范的非负十进制整数且不超uint128。

- [原冻结计划](plan/design-freeze.md)
- [失败日志](results/raw_caida_flow.log)
- [完整停止记录](results/failure.json)
- [独立v2编码修复](../round53_index_free_recheck_v2/plan/design-freeze.md)：CAIDA-flow完整33byte，MAWI-flow仍9byte；62case/7方法/预算/seed/选择算法不变。

本版源码、输入冻结、已完成URL准备和失败记录不覆盖；不能把v2的结果倒填成本版成功。不是内存压力中断，没有因此扩大资源限制。论文未改，未自动发布。

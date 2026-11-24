# Round44报告v2：仅修复重复members字段（已核验）

[最终报告](results/report.md) · [147条完整方法结果](results/main.csv) · [9条资格诊断](results/qualification.csv) · [核验](results/verification.json) · [修复协议](plan/design-freeze.md)

原第44轮3个数据审计、9个方法worker均完成，最后report在`dict(members=..., **diagnostic)`遇到重复字段而失败。错误及旧源码保留在原轮；没有静默覆盖它或假称首轮全程成功。

本v2先验证parsed.members与diagnostic.members相等，只纳入一次字段；不忽略元数据冲突。3项单测通过，源码及18个原输入归档hash冻结后运行。只读取现有结果，不训练、不重放、不改FP/配置/流/计时。

最终21个配对、147行：RA对BF+Exact128为1胜20负，对Replay10胜11负。所有3预选样本保留，未按结果挑cluster。全部成员0FN、辅助成员索引0、物理预算通过。

证据是**真实Twitter请求驱动的新静态检查点目录任务**，不是原生产KV后端NotFound，更不是该生产系统需要RA的证明。完整来源/许可/采样及语义限制见[原轮入口](../round44_trace_snapshot/README.md)。

# 第53轮v3：用户授权6GiB资源扩展，完成剩余固定矩阵

2026-11-24。用户在明确看到第53轮v2内存上限中止后选择“允许6 GiB继续”。本版本只扩展单worker RSS限制至6GiB，其余每worker1800秒、扩展矩阵7200秒、磁盘留8GiB、native单线程、串行执行均保持；再次超限停止，不自行增加限制。

## 原失败与复用

- 原v1由于CAIDA含128bit地址而在原始key准备停止，未看方法FP；[v2计划](../../round53_index_free_recheck_v2/plan/design-freeze.md)改为CAIDA-flow 33byte、MAWI-flow 9byte的完整无损表示。
- v2已完成38case/266行：URL9case，原四条流16case，MAWI24四例，COD9case；两个固定pilot通过。
- v2在CAIDA静态任务128KiB阶段观测RSS4398841856B，超过4GiB，父进程主动terminate（exit -15）。该worker未输出方法行。全轮488.294秒后停止，不是完整矩阵完成，也不声称操作系统OOM。
- 所有旧源码、冻结、结果和失败不修改。v3使用`reuse53.py`核验并逐字节复制38个已完成case，记录来源路径/SHA；不把这些行称为v3重新执行或重新计时。
- 原已验证prepared输入仅做不可写用途的hardlink，不重复下载/解析。脚本不改写这些共享文件；Shalla的新prepared输入在v3独立生成。它们是离线输入，不是部署时成员索引。

## 不变的实验

原[第53轮矩阵](../../round53_index_free_recheck/plan/design-freeze.md)62case/434行保持：全部既定预算，static once/uniform-all/Zipf1-all，seed0，原1000segments/5regions、14tree prefixes、13cache shares、RA6 top5、GT19、相同25%/75%冷tail。

本版本只新执行CAIDA静态12case和Shalla12case，共24case/168行。不会择优改seed、模型、算法、预算、工作负载或完成判据。

`common53.py`、`cache53.py`、`prepare53.py`、`test53.py`与v2字节相同；`worker53.py`仅将末尾RSS断言由4GiB改6GiB。复用器对此做精确源码比较。父监督器和报告器相应承认6GiB限制及复用来源；原12单测再次执行。原pilot结果复用，不浪费重跑，也不称新的独立验证。

完整结果完成后：434行覆盖、物理预算、全成员BF/cache零FN、Gama旧结果62例回归、两pilot非计时等价、38case来源SHA、完整负结果和最大退化全部核验。

当前授权是资源扩展，不是论文修改/发布授权。论文不动、旧前缀结果保留、不自动commit/push。MAWI24不称新holdout；本轮不冒充1146case全覆盖或Table4端到端重测。

# 第55轮v3：磁盘恢复后的pilot续跑，科学矩阵/算法不变

2026-11-25。继承[第55轮原完整协议](../../round55_exact_full_main/plan/design-freeze.md)与[v2基线修复](../../round55_exact_full_main_v2/plan/design-freeze.md)。原版接错Stacked失败、v2磁盘保护中止都保留，不改旧源码/结果。

## v2停止与资源清理

v2通过16测试与新冻结，URL64三个pilot完成；CAIDA128完成uniform-all和Zipf1-all两个pilot（382.790秒、296.649秒），在第三个once过程中磁盘可用空间跌破4GiB而被父进程停止。CAIDA worker峰值2912960512B、exit=-15，不是内存中止；其两份完整case已原子保存，第三份没有完成结果。v2总wall978.048秒，未启动正式1146矩阵。

用户明确授权删除可重建的SIS五月已解压原日志：先重新核对完整13687894566B文件SHA和2995604801B压缩包SHA，再只删除原日志。完整压缩包、prepared数据/结果/日志保留；清理后可用17963397120B，回执在docs/SIS五月可重建原始文件_授权清理回执_20261125.json。未来依赖该raw file的旧验证必须先重新解压，不能假称仍可验证。

## 精确续跑，不复活旧失败进程

- 新目录复制v2代码；common55、缓存、模型、选择、Stacked、消融、回放不变。
- `plan/reuse.json`列v2已完整5个pilot的精确来源及SHA：URL3case（完整status一起复制），CAIDA2case（仅完整case，失败status不复制）。
- v3校验case身份/SHA，仅跳过这些获准恢复的pilot；CAIDA第三例重新执行，MAWI21 pilot新执行。不拼接进程内缓存/中间状态、不读取失败未完成数组。
- 正式矩阵case复用数=0。即使pilot与formal case相同，正式1146＋4仍全部新执行。
- CAIDA续跑的`new_worker_wall_s`是新进程实测；`wall_s`为该值加原两完整case耗时的显式cost composite，仅用于既定pilot成本外推，不伪称一次worker实测时间。原v2全过程978秒和重复准备成本另外保留。

## 原限制不变

单worker/native1、RSS4GiB、disk reserve4GiB、worker7200秒、formal8小时、输出1GiB均不改；16fixture测试重新执行，新的源码/输入和复用来源冻结后启动。7例成本闸门仍生效，可能因保守外推超过8小时而停止。超限不减case/诊断/seed、不自动延长。论文、旧标签及历史结果不改，不自动push。

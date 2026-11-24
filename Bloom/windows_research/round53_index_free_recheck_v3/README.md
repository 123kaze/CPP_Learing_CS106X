# 第53轮v3：获准6GiB后仍触发内存上限

用户明确选择“允许6 GiB继续”后建立本资源扩展版本。12单测通过；v2的38case/266行和既有prepared输入按SHA复用，worker只调整RSS后置检查，算法/缓存/输入源码不变。

CAIDA静态任务128KiB进程RSS达到6535249920B，父进程按6GiB上限终止，exit=-15。worker25.773秒，全pipeline27.493秒；未产生新方法行。**本版本仅复用旧38case，没有完成剩余24case。**

- [授权与冻结计划](plan/design-freeze.md)
- [失败记录](results/failure.json)
- [资源记录](results/caida_128_process.json)
- [旧结果复用来源](results/reuse_provenance.json)
- 用户随后明确授权清理候选工作区，另立[v4](../round53_index_free_recheck_v4/README.md)，原6GiB上限未提高。

本版本源码、SHA冻结、复用记录和失败均保留；没有自动扩大资源或把后续完成倒填为本版成功。论文未改，未自动发布。

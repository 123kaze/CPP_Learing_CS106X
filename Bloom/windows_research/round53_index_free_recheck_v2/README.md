# 第53轮v2：38case完成后触发4GiB内存上限

原始key编码修复后，12项单测、两个固定资源pilot通过；完成URL、五条流（含已使用MAWI24）和COD，共38case/266行。

随后CAIDA静态任务128KiB进程RSS达到4398841856B，父进程按预设4GiB上限终止，exit=-15。该worker尚未输出方法行；全pipeline488.294秒后停止。**本版本未完成62case矩阵。**

- [冻结计划](plan/design-freeze.md)
- [中止记录](results/failure.json)
- [内存与退出码](results/caida_128_process.json)
- 用户授权6GiB后另立[v3](../round53_index_free_recheck_v3/README.md)，仍触及上限。
- 用户再授权工作区优化后另立[v4完整结果](../round53_index_free_recheck_v4/README.md)：本版38case逐字节复用并记来源，另完成剩余24case。不得将后续成功倒填为本版本全矩阵成功。

所有旧源码、冻结和结果保留；失败不是操作系统OOM证据。论文未改，未自动发布。

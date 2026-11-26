# 第55轮v4：用户授权原实现并行全跑（1146＋4case）

2026-11-25。用户在7pilot正确性通过但原8小时保守成本gate未过后选择“原实现分批全跑”（累计最多5天、每批最多8小时）。随后用户询问4GiB上限理由，并明确要求不要卡此上限、加快、多线程也可开启。本版本依照最新授权并行独立budget workers，不进行此前提出的回放优化。

继承[原科学矩阵](../../round55_exact_full_main/plan/design-freeze.md)、[v2正确Stacked接入](../../round55_exact_full_main_v2/plan/design-freeze.md)和[v3磁盘恢复](../../round55_exact_full_main_v3/plan/design-freeze.md)，不删除任何case、seed、budget、方法、消融或候选诊断。原时间gate与所有失败保留，不把它们改成passed。

## 最新资源边界（不是过滤器部署预算）

启动前实测主机48GiB、14物理/逻辑CPU；memory_pressure报告system-wide free46%，磁盘约16GiB可用。

- 最多**2个并行Python worker**，各跑不同dataset-budget，依原manifest顺序排队。不是子agent，也不是改RA算法为并行变体。
- 每worker保留原native线程=1，避免嵌套线程争抢和改变浮点归约路径；跨worker实现并行吞吐。不是默称单worker已启用多线程。
- host RSS每worker保护线8GiB，合计16GiB；disk保留4GiB，本轮输出<=1GiB。部署Filter Budget仍原KiB级值、全array/cache实占不变。
- 每budget批次最多8小时；整轮wall累计最多5天。超限或worker失败停止队列并保存完成/失败状态，无自动扩限或重启。监督器只管理其自身启动的子进程，不终止用户其他程序。

## 原实现不变的可执行核验

v4 common55.py与v3字节相同；worker55.py只把末尾host RSS断言4GiB改为8GiB，其余全部一致。runner启动时对这两条逐字节assert。变化只有并行调度、资源记录和报告允许8GiB，不是数据重分组/stream重采样/缓存优化。

7个正确pilot按源路径和SHA显式复用：URL64三例、CAIDA128三例、MAWI21/24一例。它们均已通过第53轮7方法结果回归和正确Stacked对应旧FP回归（适用时）。不浪费时间重跑已验证pilot；**正式case复用=0**。正式1146＋已用MAWI24四例全部新执行。

## 时间口径

此次并行任务用于FP/内存/FN/表图数据完整性。worker记录的selection/build/replay wall受资源竞争影响，必须标为**并行批次过程耗时**，不能作为论文中独占机器的选择加速或完整构建基准。后续正式选择/训练构建/scalability计时仍串行、同环境重复测量；这不是已经完成的工作。

原保守外推347763.25秒（96.60小时）作为单worker、重seed0诊断外推保留；不能简单除2就保证48.3小时完成，机器争用/数据差异存在。只有实际完成后报告真实wall。

论文、旧公开结果、标签不改，不自动commit/push。源码/输入/复用来源重新冻结后启动；16项fixture通过后才执行正式queue。

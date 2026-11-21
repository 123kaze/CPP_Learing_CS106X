# Round31：严格交错SQLite反馈（已完成）

**8设置、两后端、3重复，共312条计时，已独立核验。**

- [完整报告](results/report.md)
- [全部312条计时](results/timings.csv)
- [104行方法×后端中位数](results/medians.csv)
- [完成记录](results/completion.json)、[独立核验](results/verification.json)

在线放行序列与最终Cache逐字节等于原标签模拟参考，所有成员检查0FN。RA-PLBF在16个设置×后端中，6个比NoFilter快、12个比Gama快，**0个比BF+Cache快**。这是真实交错SQL反馈、Python标量API实现的结果；全部输赢和各次计时均保留。

这是针对第30轮所确认的执行语义问题的新实验；不改动冻结第6轮，不自动应用论文补丁。

- [冻结协议](plan/design-freeze.md)
- [状态说明](STATUS.md)
- [原生探测与真实SQL反馈驱动](src/online31.py)
- [正式worker](src/worker31.py)
- [完成后报告核验器](src/report31.py)

## 与旧实验的实质区别

旧路径先对整批查询按成员标签更新Cache，再执行SQL。这里逐query交错执行：

```text
probe cache/model/BF
if accepted:
    row = SQLite SELECT(key)
    if row is None:
        insert verified negative prefix
```

在线适配器不保存成员标签数组或旧Exe对象；训练/正确性参考仍可使用标签，但不进入在线反馈判断。实际SQL不存在才触发插入。全部在线运行的完整放行mask和最终packedCache已经与独立标签模拟逐项比较通过。

## 范围

8个原设置、文件/内存SQLite、3重复，共完成312条计时。除NoFilter和BF+Cache外，保留原五个学习方法；4个24KiB trace中FastPLBF48不可行，显式记录而不替换。

所有模型、查询顺序、预算和选择规则沿用原设置；GT19在这些特定计时输入上必须与原统计位级相同。每个query计时包括Python标量调度、Numba探测、SQL、返回处理、安全前缀搜索及Cache插入。不是无Python开销的原生C++极限，不是冷盘或远程服务，不报告p99。预计算特征与hash成本在查询计时外，单列披露。

在线路由改用真正的4个区域边界，避免依赖旧harness展开的1000段查表；每个member和negative-pool key都校验等价，实际部署缓冲区与旧保守预算分别记录，不把节省的元数据重新用于调优。

4项单测已通过：仅probe不插入、真实SQL反馈且不读标签、BF独立模拟状态一致、紧凑学习路由全key与旧路径一致。

**未看到完成标记并通过报告核验前，不把本轮标成完成。** 正式源码冻结后不再修改；任何失败保留原日志与partial，不自动重启内存压力失败。

# Round35：独立进程SQLite／本机TCP（已完成）

**6条固定pilot通过；8设置×3方法×3重复，72条正式计时全部完成并核验。没有人工等待。**

- [冻结协议](plan/design-freeze.md)
- [完整结果与边界](results/report.md)
- [全部计时](results/timings.csv)、[汇总](results/summary.csv)、[资源分项](results/resources.csv)
- [pilot资源门限](results/pilot_gate.json)
- [完成记录](results/completion.json)、[独立核验](results/verification.json)

## 主要结果

RA-PLBF比BF+Cache快 **5/8**，这5个设置三次配对都更快；比NoFilter快 **8/8**。但NoFilter对照本身不能证明模型的额外价值，主要仍看BF+Cache。

| 设置 | BF+Cache us/query | RA-PLBF us/query | RA/BF | 配对胜出 |
| --- | ---: | ---: | ---: | --- |
| COD1024KiB | 8.9527 | 9.1350 | 1.02036 | 1/3 |
| URL128KiB | 5.9274 | 5.8472 | 0.98647 | 3/3 |
| CAIDA256KiB | 13.2398 | 8.1626 | 0.61652 | 3/3 |
| Shalla1024KiB | 8.4120 | 6.4703 | 0.76918 | 3/3 |
| CAIDA-flow24KiB | 10.9315 | 8.6767 | 0.79373 | 3/3 |
| MAWI2020-flow24KiB | 5.5246 | 5.3044 | 0.96013 | 3/3 |
| MAWI2021-flow24KiB | 4.7606 | 5.0784 | 1.06675 | 0/3 |
| MAWI2022-flow24KiB | 4.7366 | 5.4036 | 1.14082 | 0/3 |

数值是每次完整请求流wall/N、再取3次中位数，不是单查询p50/p99。URL收益约1.35%，即使方向3/3一致也不说成大幅或统计显著改善；COD仍稍慢，MAWI21/22也未反超。

## 相比第34轮增加了什么证据

第34轮是SQLite后人工CPU忙等。本轮使用真实TCP连接、独立服务进程和实际SQL处理，没有busy-wait、sleep或netem注入。实际进程/序列化/socket成本下，部分设置的FP节省确实转化成了查询阶段时间收益。

服务端保存SQLite和完整成员hash索引，**先SELECT，返回无记录后才按需算安全前缀**。客户端只有收到实际不存在响应才插Cache，其Filter对象不保留完整成员索引/标签。NoFilter发普通GET，不计算无用前缀；有缓存的方法才请求前缀。

72次的完整放行mask、FP数和最终Cache字节均与原参考一致。服务端独立SQL/found/absent/prefix计数全部匹配客户端；所有成员检查0FN。服务进程退出后，临时数据库按本轮资源生命周期清理。

## 不能外推的部分

- **仅127.0.0.1回环，不是跨机器，也不是原生Redis/PostgreSQL生产部署。** 这是带验证索引sidecar的自定义SQLite RPC服务，不能声称任意后端原生支持安全前缀。
- 双端TCP_NODELAY、单持久连接、一个在途请求；未测试TLS、WAN抖动、真实服务排队、并发吞吐或冷盘。
- 输入特征/hash预计算、训练、模型准备、建库和索引构建在查询计时外并单列。更少查询时间不等于含全部启动成本的总时间已回本。
- 服务器索引`8*n+header`是真实额外资源，单列在backend；验证harness仍持有离线参考数据，不能把客户端/服务端RSS说成只有Filter Budget。共享服务为缓存方法维护sidecar，NoFilter不使用它；单独部署NoFilter本可不建该索引，不能把共享实例的索引内存说成NoFilter固有开销。
- 多进程与Python协议实现改变了资源和运行开销；不能把相对第31轮的时间差全部归为网络传播延迟，或当成高性能原生KV的代表。
- 保持第31/34轮成员、请求和已选结构，不按新TCP时延挑模型/份额。全部失败方向和3次重复均保留，不以pilot相对胜负决定正式矩阵。

## 复核

```sh
.condaenv/bin/python -I windows_research/round35_tcp_backend/src/test35.py
python3 windows_research/round35_tcp_backend/src/report35.py
```

5项单测覆盖hash/前缀一致性、真实SQL反馈、无索引客户端、无用前缀开销、错误协议帧。正式程序要求先通过资源/时长预检，不自动覆盖或重启失败任务。

本轮所有结果仅写实验与MD，论文没有继续改动。真实跨机器后端与更强真实工作负载仍是独立证据缺口。

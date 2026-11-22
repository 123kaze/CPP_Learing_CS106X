# Round35：本机独立进程SQLite TCP对照

2026-11-22。用户明确选择“先做本机TCP对照”。本轮不连接外部数据库、不安装Redis/PostgreSQL/Docker、不使用生产服务，不改论文。不得称为跨机器、真实远程Redis/PostgreSQL或生产部署证据。

## 目的与服务边界

将SQLite数据库及完整成员hash前缀验证索引放入独立服务进程，仅绑定127.0.0.1的OS分配端口。客户端通过实际TCP请求/响应查询；没有人工忙等、sleep或网络延迟注入。双端TCP_NODELAY，单持久连接、串行单请求，不做流水线或并发吞吐宣称。

每个被放行的请求都在服务端执行真实SELECT。确认不存在后，只有客户端请求前缀时才计算safe-prefix长度并返回。NoFilter与无缓存路径使用普通GET，不额外计算无用前缀；有缓存的RA/BF使用GET_WITH_PREFIX，成员命中也不做前缀搜索。缓存插入只用实际响应中的不存在状态和服务端长度。

客户端在线Filter对象不保存或查询完整member index；索引在服务端，单列8*n及array header。客户端的正确性参考harness可保留独立验证数据，但不传给在线函数，不把整个进程RSS说成Filter Budget。这个带sidecar索引的自定义服务不是原生Redis/PG接口的普遍能力。

## 数据与正式矩阵

沿用第31/34轮8设置、同一成员集合、同一200000请求、原RA6-GT19与BF+Cache模型/分区/预算。新增NoFilter作为系统对照。8settings×3methods×3repetitions=72timing records。各方法顺序循环轮换；前端Cache每次清空，后端SQLite预热状态保留且记录。预计算features/hash与训练不进入查询计时，准备/建库/索引成本单列。

模型/缓存选择不依赖新RPC计时，成员/hash/全pool flags、请求hash及期望FP必须匹配第31轮。全时序放行mask与最终packedCache都和独立参考实际逐字节比较；用服务端独立计数核对SQLcalls/found/absent/prefix lookups。检查所有成员不会被最终缓存拒绝。

## 小规模预检，不择优挑数据

先固定URL128KiB与CAIDA-flow24KiB，使用原200000请求的前2000个（不是重新生成2000个成员混合请求），3methods×1rep=6条pilot。核验协议分帧、标志、hash/前缀一致性、服务端SQL反馈与资源占用。

预检只用于正确性/资源/时长：用观测最慢us/query保守估算全矩阵查询时长（把所有方法均按最慢计，再乘1.5），加已存档建库准备量级。估计超过1小时、接口错误或资源不足则停止并报告，不根据RA胜负决定是否跑正式8设置，不自动缩短正式请求数。

## 协议与资源约束

固定二进制请求头：opcode:uint8+key:int64。回复头包含状态、safe length、payload length；限制payload最大长度，拒绝未知opcode/截断帧/非法响应。数据只传公开数据集的64位key ID与32-byte值；不发送成员标签、模型预测或预知不存在标记。

状态/计数控制请求在计时外。统计reset不改SQLite或Cache。服务端实际执行SQL计数独立于客户端；每个进程单线程并验证native threads。正式worker每次只启动一个服务进程，最大300万成员、SQL总量上限、socket timeout和启动timeout。数据库在新临时目录中创建，拒绝覆盖；只清理本轮创建的资源。不给NoFilter人为增加cache-prefix工作。

记录客户端wall/CPU、服务端CPU/RSS、SQLite页/缓存配置、index字节、查询/响应字节数与真实调用数。主指标是完整请求流wall/N及3重复中位数；不是逐query p99，不是并发服务容量。跨进程资源成本与前几轮同进程不同，明确披露。

## 冻结与失败

先单测，再冻结代码和输入。Pilot和formal使用同一冻结源码，输出分目录；pilot不纳入正式中位数。失败/部分日志保留，不覆盖旧轮次、不自动重启内存压力退出。完成需72条记录、全部查询/缓存/服务端计数核验通过，论文不自动更新。

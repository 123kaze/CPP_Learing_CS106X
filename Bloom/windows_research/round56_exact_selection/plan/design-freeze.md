# 第56轮：exact-key原实现独立串行选择成本

2026-11-26。承接用户“主实验全部无索引重跑、都要计时”的授权；第55轮FP矩阵已完成。本轮只完成TODO6中的选择成本子项，不冒充完整训练构建、在线query或scalability全部完成。

## 固定比较

- 原tab:cost的八设置：COD1024、CAIDA256、Shalla1024、URL128、CAIDA-flow24、MAWI20/21/22各24KiB。
- 静态数据：seed0、zipf1.0-全部、原10M流的前25%学习与后75%tail；flow用原真实时序流。
- Gama、Replay、RA6-top5；14tree×13share原grid，GT19、DP、rawkey exact CLOCK、所有预算与key宽度不变。
- 直接使用第55轮冻结common55/E5/K/RA6原实现，不引入此前round15的local-key加速或其他新优化。**计时结论限定为这套full-pool研究实现**；不将其速度比解释为对任意优化Replay实现的下界。
- 每设置每方法3次独立进程测量，共72formal workers；rep0顺序Gama/Replay/RA6，rep1 Replay/RA6/Gama，rep2 RA6/Gama/Replay。一个时刻只运行一个实验worker，native线程固定1。

## 计时边界

1. 数据读取、冻结输入核验、原训练模型/分数读取、14prefix segment准备、原流生成各自记录，但不计入选择。
2. 每worker用同一输入完整warm-up一次选择，明确记录warmup时间，释放候选与GC；不保留warmup结果充formal。
3. 选择计时从原始learning数组开始：Gama建全部14无cache候选并选最小估计FPR；Replay建可行全grid并在learning上做原early-stop exact回放（包含bincount）；RA包含GT19计数/rate、全候选预测、top5真实构建和bucket refinement。
4. 每个方法独立构建所需候选，无跨方法候选复用，不拿RA的top10总时间当top5。每worker仅一次正式测量，另记process CPU时间。
5. 选择后真实cold-tail exact回放与全member检查单独计时，并与第55轮对应方法的树数/share/FP/flagsSHA/cacheSHA/物理bytes完全回归。该replay不是包含特征提取/模型调用/backend的query latency。
6. 源码/输入SHA核验、数据和模型准备、warmup、stream生成、selection、verification和worker总时间分别留档；不把训练复用称为训练用时。

## 状态/字节口径

部署model/BF/metadata/array headers/cache继续严格计费，无成员验证索引。rawkey blob/offsets和模型输入是主机工作区，单列，不当作全系统免费。

learning trace记录逻辑view bytes及其实际保留的owning base数组（10M全流仍由离线driver持有），不能只拿20MB视图冒充host总占用。RA keys/counts/rate三数组分别计payload与sys.getsizeof物理bytes，不能只报旧16D而省rate；Replay的bincount工作缓冲计为选择期临时量。peak RSS为整个worker（含warmup），不是选择阶段独立峰值。没有把count状态比称为全进程内存比。

## 固定资源闸门

- URL128与CAIDA256各3方法先做pilot（共6worker，不复用为formal）。warmup/选择/回归同formal。
- 保守成本外推：72×pilot最长worker耗时＋120秒；须≤8小时，否则停止并留档，未经用户新授权不扩大。
- 串行、每worker host RSS<8GiB；每worker≤1小时；整个本轮≤8小时；磁盘保留4GiB，输出≤128MiB。
- 运行前记录机器/负载；本实验不运行并行worker，不终止用户其他程序，也不声称操作系统绝对无其他负载。CPU时间和wall一起报告，以观察调度等待。
- 不为获得加速比删rep或重复到满意；任何错误/超限停止整轮，保留已有case与失败，无自动重试。
- 不与第54轮或其他新增实验并行。不改论文，不自动commit/push。

代码与引用输入冻结、测试通过后才运行pilot；冻结后修改必须另版本。

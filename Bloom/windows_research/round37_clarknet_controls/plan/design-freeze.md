# Round37：ClarkNet五方法对照与固定配置权重消融

2026-11-22。第36轮在未测任何方法FP前，依据冻结数据资格门槛选出ClarkNet。Saskatchewan未过90%的404保留率门槛，不进入本轮，也不修改该门槛。ClarkNet为1995年两周回溯稳定子集，不是现代、大规模或动态前瞻部署证据。

本协议在本轮首次BF构建/尾段方法效果评估之前冻结。只使用第36轮生成的完整ClarkNet NPZ，SHA256固定；不再调整数据、排除冲突、特征或记录顺序。旧实验/论文不修改。

## A. 五方法同预算对照

- seeds=3601/3602/3603，与第36轮相同。使用round27冻结的prepare/evaluate辅助函数，拆分规则不变：开发期已出现的负key 10%训练、10%验证，其余为查询池；全部member进入BF，50%用于模型训练。首25%已解析GET序号为开发边界，负查询学习比例并非必为25%。
- 预算事前公式：ceil(n_members * b / (8*1024)) KiB，b=2/4/8，最低4KiB。本数据n=32581，得到8/16/32KiB。预算为全部Filter模型/路由/header/BF/cache，不是只BF payload；后端完整成员hash索引另列。
- 模型固定LightGBM 200树/31叶/lr0.1/1线程，全部原树数网格和13项cache share网格；不按尾段选择。前16树的开发AUC须复现第36轮诊断。
- 方法：Gama（cache=0）、Replay（完整grid+学习流回放）、RA-global（GT19学习摘要，原validation h分配）、RA-PLBF-GT19（冻结RA6 top5）、BF+Cache（相同13份额，学习回放选取）。不把事后NR32或GT归一化变体混入主方法。
- 所有方法相同自然negative学习/尾段序列；tail冷Cache。完整尾段CLOCK回放包括static reject，不跳过可能改变refbit的prefix alias。查询序列hash/数量固定。真实标签只用于离线静态任务与安全索引，这不是新的SQL/TCP在线实验。
- 3预算×3seed×5方法=45行，全部保留；FP按每对(FP_A+1)/(FP_B+1)计算，结果不改资格、预算或样本。共享日志的3seed不当独立工作负载，不做挑选显著性的检验。
- 分别计时训练、prefix评分、索引、GT摘要、JIT准备、每方法构建/选择、尾段回放。尾段回放用已计算的static flags，不是包含模型计算的端到端查询延迟。

## B. 固定配置配对消融：额外27行

这是独立诊断变体，不冒充冻结RA6算法，也不把A中RA-global/RA差异全归给权重。

每budget/seed固定cache share=10%；只按validation的Gama DP criterion（同分选少树）从该份额的可行树中选一个h配置。固定其**模型、DP分区、真实member region counts、总BF位预算、Cache字节/布局、成员/查询hash、学习及尾段序列**。若某预算无可行anchor则记录不可行，不改份额或树网格。

将1000个segment汇总到固定region。使用同一连续截断分配器与同一实体packed-BF builder比较三个权重：

1. `h`：固定validation smoothed h。
2. `traffic`：冻结GT19 population在cache slots=0时的有效到达质量。
3. `miss`：在`h`连续分配epsilon及固定10% cache slots下，冻结set-associative Che近似算出的miss质量；只算一次，不利用tail或实际静态FP精排。

traffic/miss加入原1e-6总质量乘h的floor后按region汇总。每arm均用真实region member数的capped连续解，逐region向下取整位数、同一整数最优probe规则，packed BF和完整CLOCK回放。本轮不重新DP分区；不把分区/树/cache的改变混入权重效应。三个arm分别留同样header及路由保留量，禁止把未用字节偷偷给某一arm。

额外traffic arm用来区分流行度/请求质量重加权与扣除缓存可吸收部分：miss比h好，不自动说明cache-aware部分额外有效，还需看miss比traffic的结果。

同时记录固定miss系数下的连续h/miss最优目标与AM/GM因子、是否双内点；实体有限CLOCK会随BF分配改变实际缓存驻留，不满足外生固定T，因此该因子不作为真实CLOCK收益保证。整数BF与有限轨迹可能负收益，全部保留。

资源：沿用E5真实模型、路由和12数组header的保守保留量；实际BF payload及cache实占<=Filter budget，全成员BF查询与最终Cache成员检查0FN。后端索引8*n+header单列；数据矩阵、学习状态、候选工作区另列，不声称进程RSS在Filter预算内。

## 执行边界

先人工小数组/fixture单测，之后冻结源码、输入与依赖hash。三个seed顺序运行、每次一个worker，caffeinate护航。失败留日志，不覆盖或内存压力后自动重启。全部45+27行完成才勾选完成；本轮未获新push请求，不自动发布。

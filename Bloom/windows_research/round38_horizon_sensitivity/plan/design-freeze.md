# Round38：预测H误设敏感性（先固定真实尾段，再改变预测输入）

2026-11-22。用户要求先push第36/37轮再做非论文补充；两仓已发布（CPP ba5274d；ra-gama b41ff67）。本轮不修改任何旧冻结源码或论文，不调用本地C/C++构建器。

## 要隔离的问题

旧E10改变学习比例、prefix bits和ways，虽然固定评估窗口，但总是把实际`len(tail)`传入选择器，不能替代H误设实验。本轮冻结学习数据、真实尾段、模型、成员/负例池、预算及cache格式，**只改变RA6两阶段预测所接收的H**。不截断/复制/扩充真实尾段，不重新训练选择更有利模型，不以尾段效果选H。

四个预测规则：

- `quarter`：max(1, floor(H_actual/4))。
- `matched`：H_actual，作为有正确长度信息的敏感性参照，不称为部署时可知未来。
- `fourfold`：4*H_actual。
- `three_learning`：3*L，只依赖已观察学习请求量，不读取尾段。它是预设启发式，不承诺最优；HTTP经过key/status过滤后H_actual不必等于3L。

实际/预测比例与预测/实际比例都保存，避免把0.25×方向说反。四个规则即使得到相同整数H也全部重新选择并计时；相同H须逐字节复现结构、flags和完整尾段cache状态。

## 固定矩阵：21 case keys × 2格式 × 4规则 = 168次选择/评估

1. 论文数据4例：COD1024KiB、URL128KiB、CAIDA256KiB、Shalla1024KiB，`zipf1.0-全部`，seed0，原完整10M流的25%/75%。
2. 原真实流4例：CAIDA-flow、MAWI2020/2021/2022-flow，各24KiB、seed0，原全流25%/75%。
3. TCP-only4例：CAIDA32KiB、MAWI2020 64KiB、MAWI2021 41KiB、MAWI2022 64KiB，seed0，冻结构造与完整原流；不将旧轨迹新任务称作新独立留出。
4. ClarkNet9例：8/16/32KiB × seeds3601/3602/3603，完整复用第36/37轮NPZ、拆分、200树训练规则和自然序列。原3seed都纳入，不因第37轮输赢选seed。

两格式为verified-prefix index与fp64。每个worker只用一种格式；E5.K采用既有模块替换方式，RA6本身和GT19摘要原样使用，不混入NR32、零树或归一化变体。fp64不建立/持有完整排序成员索引，不计算safe prefixes；构建与验证用的成员hash数组仍属于harness/build状态。

`matched`回归参照：原12例×2格式的24结果须复现round19汇总的修复后RA FP；ClarkNet的9个index结果须复现第37轮配置、FP和全pool flags hash。ClarkNet-fp64的9个matched配置是新补充结果，不重命名为原留出前证据。

## 计时、验证与报告

- legacy prepared arrays/model仅加载，不下载或隐式重训；ClarkNet按旧固定规则重新训练，前16树开发AUC须复现第36轮，query hashes须复现第37轮。
- 逐worker单线程，顺序30个worker；不得并行多个大成员集worker。加载、模型/score准备、索引/safe-prefix准备、流构造、GT摘要、JIT、选择/实体构建、payload重建检查、候选诊断、完整尾段回放和全成员cache检查均分别计时。用于物理回归的额外payload构建不算一次选择的正常成本。
- 预热模型/segment统计及通用kernel后，四规则按case索引循环移位顺序运行；不把单次wall measurement或共享seed当独立时延重复。
- 选择器API不接收tail数组。观察器仅转发并记录原candidate_table和bucket_prediction的H与返回对象，不重算候选表、不改排序；异常后恢复模块绑定。
- 验证全部预算、实体BF全成员接受、完整negative尾段处理数和最终cache成员命中数。index必须0FN；fp64记录有限成员命中与理想非对抗hash假设下`min(1,slots/2^64)`的单query界，不能称普适或生命周期零FN。
- 每条记录保存完整payload数组dtype/shape/hash、候选stage1 rank/score/weights hash、模型/份额/slots、实际FP、预测FP、最终cache hash；与matched比较配置/位图/候选top5变动，逐案例(FP+1)比值先算再聚合。比matched好也只是此固定样本的结果，不能据此事后选H。
- 分开报告index/fp64、论文数据/真实流/TCP-only/HTTP，不寻找新的显著性分组。保留全部不变、变好和变差的案例。
- 这不是开放式流自动重建实验，也不是新的端到端数据库计时。H可解释为下一次计划性复核/重建前的预计negative请求数；动态更新成员、模型或路由仍需协调失效/重建，实验不会证明无限期运行保证。

先人工fixture单测及输入存在性核验，随后冻结代码和输入hash再开始。失败留档，不覆盖、不自动重试；内存压力杀死不得自行重启。

# Round39：学习期增量访问、辅助索引与有条件回本分析

2026-11-22。第38轮168条H误设实验先完成并核验后开始本轮。只使用原有数据、冻结算法和已归档matched-H配置；不新增数据集、不重选H、不改论文，不执行数据库压测或C/C++编译。

## 问题与边界

学习期L条negative queries全部查询后端，不等于相对基线多出L次访问。成员查询在无FN的两种方法中都应访问后端，做差时抵消；真正额外negative访问为`L - baseline_learning_backend_calls`。若两方法共享同一次在线学习采集，或历史标签日志已存在，获取标签的**增量**访问也不同。

本轮提供精确计数回放和参数化时间模型，不冒充实际测量了完整在线学习/远程部署时间。预计算flags回放不计真实模型/特征抽取时延；不会将包含全pool评分验证的harness时间冒充生产startup成本。

已有日志必须包含完整查询与可信标签；只有经过现有filter后到达backend的日志会产生选择性缺失。若已有一个与当前成员快照一致的严格zero-FN过滤器，其拒绝本身可作为negative证书，只对放行查询查backend，就可能在不增加backend调用的条件下采集全部标签；仍要支付完整入口日志/计数CPU与内存。这是不同的在线采集协议，本轮不将其当作已经实现或验证过的主方案。不能把fp64 cache命中单独视作严格negative证书，也不能在成员/模型版本不一致时使用该推论。

## 固定数据与比较对象

复用第38轮同21 case keys（4论文Zipf、4真实流、4TCP-only、ClarkNet3预算×3seed）及index/fp64两格式，共42个设置。所有学习/尾段hash须匹配第38轮；RA只取`matched`行的冻结配置与FP，不取误设H中效果更好的行。

三个部署比较分别报告：

1. **新在线学习RA vs 已经可用的Plain BF**：Plain BF无学习选择、cache=0，从学习开始前即已部署。读取旧legacy的BF学习/尾段计数；ClarkNet缺失者新建同预算Plain BF并计数。对旧结果另与原组合表核对。学习增量`L-FP_BF,learn`，尾段节省`FP_BF,tail-FP_RA,tail`。
2. **新在线学习RA vs 预设10% Cache的BF**：10%在实验前固定，不使用当前学习窗口挑份额。该baseline在学习阶段真实CLOCK回放并将同一cache状态带入尾段；RA按旧协议学完后冷启动。每个设置新建并完整回放一次，共42个warm-baseline控制；index安全插入使用完整成员索引，fp64不建立该索引。
3. **同享标签来源后，两者一起部署**：RA与学习选份额的BF+Cache共同承担相同在线标签采集（或标签来自已有历史日志），增量学习访问=0；都在尾段冷启动。legacy复用冻结BF+Cache档案，ClarkNet两格式重建原13份额并学习回放选择，index须复现第37轮，fp64明确为新补充。不得把这个当前窗口挑出的BF+Cache反过来称作学习开始前已可部署的baseline。

在当前negative-only评估协议下，比较中的成员访问在无碰撞/FN条件下抵消，因此无需凭空为旧流造成员查询。用于索引资源、时间外推的成员比例另外显式作为参数，不把假定比例写成观测。

## 逐项成本与正确性

- 记录输入加载、hash/索引构建、safe-prefix预计算、BF构建、学习回放、连续尾段回放、全成员检查、额外BF+Cache网格选择及归档核验wall时间。仅一个worker进程运行，30个worker顺序。
- verified-prefix的部署辅助索引为8*n+ndarray header，仅有缓存时需要；Plain BF不需要，fp64不需要。construction/harness持有的成员hash与输入数据不等于部署backend索引。
- index查询安全依赖静态完整成员集合、实际absent反馈和正确prefix验证；该回放是标签确认的计数模拟，不是新的SQL反馈计时。fp64检查有限member/query fingerprint不相交，保存实际成员检查；一般键域仍非严格零FN。
- 一定要报告Filter实占和required backend-index字节之和，不能说整个进程或所有系统额外内存都在Filter Budget中。已存在完整hash索引时，新增索引字节可为0；只有原始key有序不能推出hash-prefix索引免费。
- 另外核算学习状态：原GT19 `state_bytes`只统计keys＋counts的16D字节，实际摘要另有rates的8D，三数组payload共24D；与8L原始学习索引轨迹payload分列。记录本批D/L，验证全distinct的16D/24D相对8L反例；payload不冒充含header、Population临时空间或整个RSS。本轮为核算构造后释放摘要，相关时间单列。
- fp64仍有用于有限fingerprint交集核验的临时工作区；“无索引”指不建立或保留供prefix验证使用的完整成员排序索引，不声称验证harness没有成员数据或临时排序内存。
- 所有baseline均断言预算及BF全成员接受；index cache不得拒绝成员。warm baseline不在阶段边界重置cache；其学习/尾段FP绝不混成cold结果。

## 回本公式（显式假设，不是新计时）

令ΔL为额外学习backend调用数，s为当前尾段每negative query节省的调用数，A为除backend调用之外的新增startup、学习处理、训练、索引和重配置成本净差（秒；本轮示例限定A>=0），C为每backend lookup及相应交互的基本成本微秒，d为每**总查询**新增非lookup处理成本微秒（含前端模型/特征/缓存，以及后端按需prefix验证的摊销差额），p为未来成员查询比例。A不能漏掉学习统计CPU，也不能把原本两边共同支付的准备工作重复计费。若未来负载维持这个观测节省率，则

`ΔT(N) = A + ΔL*C/1e6 + N*[d - (1-p)*s*C]/1e6`。

只有`(1-p)*s*C-d > 0`时才有正的持续收益斜率；否则增大N不会偿还非负startup/学习成本。这是恒定成本/分布外推，不保证实际未来cache状态、工作集或负载不变。若每个H周期都重新采集/重建，A与ΔL须按周期重复计费，不能把一次启动成本外推到无限期。A、C、d、p须部署实测；本轮不能凭空补齐缺测组件。

除符号公式和backend-call-only下界外，固定六个**示例参数**展示敏感性，不根据结果选参数：
- calls_only：A0s、C10us、d0us、p0。
- startup_1s_backend_10us：A1s、C10us、d0us、p0.1。
- startup_1s_backend_40us：A1s、C40us、d0.1us、p0.1。
- startup_10s_backend_40us：A10s、C40us、d0.1us、p0.1。
- startup_1s_backend_100us：A1s、C100us、d0.1us、p0.1。
- positive_90pct：A1s、C40us、d0.1us、p0.9。

即使是假定C40us，也不称为真实远程服务或第35轮的纯网络传播时间。负斜率、不可回本、小收益及所有场景均保留。首次查看本轮计数前冻结源码/输入和单测；失败保留，不修改冻结代码或自动重启。

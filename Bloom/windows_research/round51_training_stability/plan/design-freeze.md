# Round51：极不平衡训练稳定性消融（开发段，明确新配方）

2026-11-23。接续SIS完整文件探索，非独立holdout。第50轮原配方训练约137万正key与98–116负key，16tree开发AUC0.33–0.45，member99.8%集中bin999，rawscore出现上万/十万数量级。本轮检验训练配方而非倒转标签/分数，不改第50轮结果。

固定4种配方，各3seed5001/5002/5003，共12个16tree模型：
1.original：与第50轮同样的无权重/不限leafstep；逐seed AUC复现。
2.balanced：每个训练样本权重N_train/(2*N_its_class)，两类总权重相等且平均weight1；不减少/重复抽样key，避免绝对Hessian尺度无意改变。
3.clip_only：不加权，仅max_delta_step=1；learning_rate=.1，所以每轮leaf增量受限。
4.balanced_clip：相同balanced weights加max_delta_step=1。

原16tree/31leaf/lr.1/单线程及20维query词法特征/split完全不变；不增加namespace词表，不读取status为特征，不改变H/stream/keypool，不查看实体filter FP。诊断记录rawscore范围/有限性、AUC、1000segment占用/饱和、训练/评分/时间/工作区。Clipraw范围与init_logit±16*.1核对；balanced预计init_logit约0，但用实际训练权重求值，不假定。

**不是看完结果挑四者中最高者**：预选后续候选只有balanced_clip。进入后续方法比较的开发门限固定为至少2/3seed的balanced_clip AUC>=.70且比original增加>=.03，所有rawscores有限并满足clip界。其他2个配方仅隔离原因，不能拿更有利的结果换主候选。即使通过，也只说明值得另冻实体filter验证，不是RA已赢。

若后续运行，原配方与balanced_clip完整并列，Gama/Replay/RA-global/RA都给相同配方和训练数据；BF+Cache不被迫付不需要的模型成本。新配方不得追认给旧冻结RA6/Gama结果或旧MAWIholdout。当前源文件/负流已经做过探索性统计，因此不是未读的独立数据；真正外部应用/时间段验证仍需新协议。

资源：3顺序workers，每worker600s/RSS4GiB，完整输入/源码SHA冻结；5项以下小型fixture先验校验weights/clip/单调score方向。原data50输入只读，不修改原计数/原数据。rawURL不发布，不改论文，不自动push；失败留档不自动重启。

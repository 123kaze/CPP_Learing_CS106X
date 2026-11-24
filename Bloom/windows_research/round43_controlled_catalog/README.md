# Round43：构造并验证RA获胜条件（已完成，明确为合成数据）

[事前冻结协议](plan/design-freeze.md) · [完整报告](results/report.md) · [378条主比较](results/main.csv) · [162条固定配置消融](results/controls.csv) · [1296条真实SQL计时](results/timings.csv) · [成本阈值](results/cost_crossovers.csv) · [独立复算回执](../../docs/round43_evidence_20261123/verification.json)

**这轮不是再找必胜数据后隐藏失败，而是事前固定强/弱模型、三种关联、三预算、三seed，所有54组合完整保留。找到了FP和实际查询阶段的胜出条件，但不能宣称含启动成本已回本或证明生产KV普遍适用。**

8项小型fixture测试通过，50个源码哈希在首次完整目录生成前冻结；pilot只按资源/时长判定，不看AUC/胜负。6个正式worker顺序完成，全轮316.29秒（包括pilot/测试/报告）。没有后续改生成器、预算、tail或H。冻结前一次linspace镜像浮点断言失败已在[开发记录](plan/pre-freeze-development.md)披露，修正发生在完整数据生成前。

## 数据如何构造

每个seed/强度：65536members、16384negative-train、16384negative-validation、65536negative-query-pool。真实key域就是uint64，SQLite存其完整8bytes；高8bits是可在查询时取得的namespace特征，其余56bits独立随机。不从标签或频率编码suffix，特征不读取标签。

- **弱模型a=0**：正负namespace同分布，16tree开发AUC约0.4984–0.5010。
- **强模型a=6**：正负namespace分布强烈但非确定地偏向两端，开发AUC约0.9874–0.9876。这种强可学习性由实验者刻意控制，不能叫天然生产统计。
- 实际所有6个目录的256feature bins都有members，65536个query-negative keys全部与members共享同值特征。单纯“该namespace是否有member”的安全规则无法拒绝任何负key，不是protocol式完美标签规则。
- 在5个固定feature区内分配不同Zipf指数：neutral全1；high_hot为.4/.7/1/1.3/1.6；low_hot反向。各区总请求概率严格保持该区的negative-key比例，只变区内集中程度。
- 每流100万请求，前25万learning、后75万tail；同目录三个关联用共同随机uniform draws映射各自CDF。两个关联方向和neutral全部报告。

完整64bit cache保存rawuint64的**双射hash**，所以在这个精确域内就是精确key缓存，不需要成员验证索引，不套一般fingerprint的S/2^64概率界。该特例不适用于先把任意字符串压缩为64bits的系统，不能追认给旧fp64泛域实现。

## 1. FP：强模型下赢BF，弱模型下仍通常输

每个表格单元包含3预算×3seed=9对。比值是逐case加1平滑比中位数。

| 强度/关联 | RA vs BF 胜/平/负 | RA/BF比中位 | RA vs Replay 胜/平/负 |
| --- | --- | ---: | --- |
| 弱 / neutral | 0/0/9 | 1.196463 | 5/0/4 |
| 弱 / high_hot | 0/0/9 | 1.119390 | 9/0/0 |
| 弱 / low_hot | 1/0/8 | 1.118551 | 9/0/0 |
| 强 / neutral | 9/0/0 | 0.008737 | 7/1/1 |
| 强 / high_hot | 9/0/0 | 0.002457 | 6/0/3 |
| 强 / low_hot | 9/0/0 | 0.054726 | 8/0/1 |

强模型组对BF27/27胜，对Replay21胜1平5负。不要把对BF的大幅改善全部归因于重加权：这一组连Gama本身也很有区分能力。分配收益要看Replay和下述固定配置控制。

### 强模型的全部预算FP中位数（每项3seed）

| 关联 | KiB | Gama | Replay | RA-global | RA | BF+Cache |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| neutral | 16 | 7928 | 3406 | 3437 | 3142 | 197761 |
| neutral | 32 | 3290 | 381 | 375 | 366 | 62797 |
| neutral | 64 | 313 | 35 | 43 | 32 | 3776 |
| high_hot | 16 | 7613 | 1627 | 1627 | 1457 | 295491 |
| high_hot | 32 | 3262 | 180 | 180 | 178 | 108126 |
| high_hot | 64 | 251 | 18 | 23 | 26 | 11466 |
| low_hot | 16 | 7798 | 5277 | 5807 | 3788 | 41135 |
| low_hot | 32 | 2752 | 466 | 446 | 347 | 10031 |
| low_hot | 64 | 489 | 35 | 38 | 30 | 574 |

64KiB有很低的绝对FP，不用巨大比值放大意义。high_hot64KiB的RA中位FP26高于Replay18，是保留的反例。

## 2. 实际SQL查询：小预算、便宜小模型、负查询多时出现胜出

每个主case另测两个合成member比例，各20000条请求、4方法、3次重复，合计1296条计时。原始8byte key解码、hash、特征、model/cache/BF、真实SQL和反馈全部在timer内。没有人工等待。这里的member比例由实验者设定，不是来自真实流。

| 条件 | RA比BF更快 / 总设置 | 配对耗时比中位 |
| --- | ---: | ---: |
| 弱模型，约10%members | 0/27 | 1.458712 |
| 弱模型，约90%members | 0/27 | 1.149998 |
| 强模型，约10%members | 8/27 | 1.245794 |
| 强模型，约90%members | 0/27 | 1.120621 |

**强模型组整体时间中位数仍输BF，不能用8个胜出点盖掉19个失败点。** 8次胜出中6次是16KiB（neutral/high_hot各3seed），2次是high_hot32KiB；64KiB全部未赢，BF本来就很少访问backend时模型额外成本难抵消。

按3seed聚合的强模型/10%member配对耗时比：neutral16KiB0.765884、high_hot16KiB0.633587、high_hot32KiB0.979421；其余6个关联/预算组>1。

### 一个示例，不能替代全矩阵

从已冻结矩阵中取strong/high_hot/16KiB/seed4301说明：

- 全75万negative tail：RA1457FP、Replay1653、BF295491。
- RA仅1棵树，model payload670B，完整Filter15054B，其中cache3264B；BF实际16384B，其中cache312B。双方额外成员索引均0。
- 独立的20000条混合计时窗口：2068members；RA2170次SQL、BF9109次SQL。
- RA1.872us/query、BF2.972us/query（各自3次中位数）；正确的配对时间比0.633587，约少36.6%查询阶段时间。
- 这个短窗口RA FP102、Replay79，与完整75万tail排序不同，不能混用两个窗口声称RA在任何长度都胜Replay。
- RA额外计入启动成本约3.075秒；当前窗口省下约0.02165秒，因此**还没回本**。按此窗口速率恒定外推需约2840364个后续总查询；不是实际跑了284万条，不保证warm-cache/分布漂移后保持速率。

## 3. Backend更贵只在少查后端时有用

cost_projections.csv给出额外每lookup0/5/20/100us的**条件投影**，不是新实测数据库时延。

强模型、10%member下，query阶段预测胜出分别8/12/16/24（分母27）；90%member下0/0/4/15。弱模型在这些成本上仍0/27胜（两种member比例）。RA本来更多lookup的设置不能靠把backend变慢救回来。

即使加到100us，全部组的单个20000请求窗口也未摊平所计入的额外启动成本。投影含共享历史标签假设；不代表标签采集、周期重建或在线部署生命周期免费。

## 4. 固定配置重加权控制与选择时间

每case固定validation选出的树、分区、10%cache及BF位预算，只改h/traffic/miss权重。162行完整保留：

- 弱模型27对：miss/h16胜11负，比中位0.988854；miss/traffic16胜11负，0.991684。
- 强模型27对：miss/h18胜9负，0.941718；miss/traffic19胜1平7负，0.938776。
- 40/54符合连续正支持/双内点条件并核验AM/GM等式。实际CLOCK的T不是外生固定，所以实体改善不作定理全称保证；7个强模型miss/traffic退化仍保留。
- 含GT统计的RA选择对Replay：弱/强各22/27更快，配对耗时比中位0.903298/0.969237。这里learning只有25万条，不能继承旧100M实验49×。

## 再现与证据边界

[数据schema与生成入口](DATASET.md)。本地cache保存6个目录和18条完整生成流，SHA在workerJSON；缓存目录不发布。`src/catalog43.py`的固定种子和概率规则可重建，非外部真实数据。完整性只读检查：

```sh
.condaenv/bin/python -I docs/round43_evidence_20261123/verify43.py --inputs --output /tmp/round43-verification-new.json
```

输出路径必须不存在；公开checkout没有本地cache时去掉`--inputs`。冻结源码依赖缺失会标partial，不能冒称核验完整。正式run43拒绝覆盖旧结果，不在原档案上重跑来刷新计时。

本轮证明的是**存在可复现的受控获胜条件**，不是生产普遍优势；强组AUC非常高、key短且特征极便宜，这些前提都需要在真实应用另行核验。真实来源筛查见[单列MD](../../docs/真实KV来源筛查_20261123.md)。论文、旧冻结实现和旧投稿标签未修改，本批未自动push。

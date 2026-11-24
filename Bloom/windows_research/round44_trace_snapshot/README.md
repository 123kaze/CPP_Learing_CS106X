# Round44：真实Twitter请求驱动的检查点目录（方法实验完成；报告v2已核验）

[冻结协议](plan/design-freeze.md) · [来源与CC BY4.0许可](SOURCE.md) · [下载回执](results/downloads.json) · [最终报告v2](../round44_report_v2/results/report.md) · [147条结果](../round44_report_v2/results/main.csv) · [独立复核](../../docs/round44_evidence_20261123/verification.json)

**本轮没有证明RA在这个真实轨迹驱动任务中更值得部署：对BF+Exact128为1胜20负，对Replay为10胜11负。** 三份样本事前固定、全部运行，未因AUC较低或RA输而替换cluster。

## 真实性的准确范围

- 原请求来自Twitter2020Mar公开缓存轨迹，固定upstream commit`1c503676d6972d4394a360e09162149a6c00f516`下cluster001–003，各100万条原始记录。下载165952560B，334.10秒，长度/Git blob SHA1/SHA256全部核验，无重试。
- 原轨迹没有经核验的完整后端成员快照或GET Found/NotFound标签。因此另定义**不可变检查点曾见key目录**：前25%GET出现过的所有key组成M；接着25%learning、后50%tail查询是否在M内。保留原始记录顺序，不重采样，不用未来补目录。
- 这是B类“真实轨迹驱动的构造任务”，不是原Twitter KV的实际NotFound，也不是生产方已经部署该去重任务的证据。不能把cache miss、value size0或本任务negative改名为原backend不存在。
- 样本GET时间范围分别0–93、0–203、0–943秒，时间回退46/66/55次。公开文档没有明确样本选择/采样方法；不能称覆盖完整一周、所有请求严格时间有序或三个独立应用。

## 全部结果

3个目录分别5836、6456、40952members；负key3373、12402、57682。三者都通过预设规模门槛。预算为2/4/8bits/member向上取KiB、最低4KiB，重复预算去重，因此前两个各6配对、第三个9配对，共21；七方法147行。

| 样本 | AUC16中位 | RA vs BF 胜/负 | RA vs Replay 胜/负 |
| --- | ---: | ---: | ---: |
| cluster001 | 0.573436 | 0/6 | 6/0 |
| cluster002 | 0.614198 | 0/6 | 0/6 |
| cluster003 | 0.501172 | 1/8 | 4/5 |

整体RA/BF加1平滑比中位3.776。唯一vsBF胜例：cluster003/seed4401/40KiB，RA1704、BF1735，仅少31FP，不拿它作稳定部署优势证明。

ZGate21/21在learning选择BF，tail与BF相同；相对纯RA仍会丢掉上述一例小幅优势。付过RA搜索/训练的fallback不等于一开始就没有模型成本。

### 为什么“真实重复很多”仍不够

- cluster002评估混合tail约75.6%是本任务negative，learning重复比例中位97.635%，但region重复差仅约0.0024–0.0037，模型AUC约0.61。
- 4KiB组三seedFP中位：PlainBF35083、BF+Exact1858、RA101708。Cache本身很有效，但分配给模型并没有赚回预算。
- cluster001的4KiB/seed4401，RA model payload670B，routing181B、header reserve1616B，BF位payload1555B；Plain BF/no-model可以有3952B BF payload。不能只看“模型670B很小”忽略其余部署结构。
- cluster003有region重复差约0.30–0.35，却几乎没有可学习区分能力（AUC约0.50），仍大多输BF。
- 所有negative与member的特征重叠比例较高（中位约77%/85%/94%），重叠不等于有足够可学习性。简单key长度支持规则各tail仅拒绝2/67/1条negative，不能解释主要结果。

这组结果支持的是条件边界，不是“所有真实KV都无需learned filter”。匿名化和仅24维固定词法特征限制了本次表示能力，不能直接推断原始业务语义不可学习；也不能看到结果后改特征并把新结果当首次独立留出。

## 正确性、成本与失败留档

7项解析/snapshot/split fixture测试通过；9个正式worker全部complete，合计40.49秒。完整pipeline到报告失败65.41秒（不含下载）。所有Filter预算通过、额外成员索引0、静态BF成员和最终精确key cache0FN，真实混合顺序的调用计数与负流FP一致。

缓存为Exact128：完整匿名key字节相等才命中，超长绕过；本批无>128byte key。哈希仅用于BF和桶分配，不作为负缓存的精确key身份。静态同版本/真实精确absence反馈前提不变。

**原报告失败必须保留：** `report44.py`合并资格元数据时重复指定members，报`TypeError: dict() got multiple values for keyword argument 'members'`。旧report.log、failure.json、源码都未改。另立[round44_report_v2](../round44_report_v2/README.md)，3项单测后冻结，只读取9个已完成结果，修复汇总，没有重跑解析、模型、回放或改变任何FP/配置。

独立[verify44.py](../../docs/round44_evidence_20261123/verify44.py)再次核验所有来源/源码hash、实际目录严格等于第一季度GET集合、原始匿名key到ID的一致性、147行预算/成员检查、ZGate来源及所有配对算术。

当前只测准备/训练/选择/回放，**没有本数据的真实SQL端到端延迟**。不能从FP表或第43轮合成时延声称这里会整体加速，更不能用外推替代训练/学习回本。

不改论文、旧标签和已冻结代码；没有按tail追赢家；本批未自动commit/push。

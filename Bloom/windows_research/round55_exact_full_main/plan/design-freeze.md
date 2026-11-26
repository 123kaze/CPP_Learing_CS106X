# 第55轮：完整主表及直接图表依赖，无索引完整key重跑

2026-11-25，用户将全量主实验迁移exact-key设为最高优先级。第54轮审查补充暂停（未正式执行）。本轮不修改论文、旧源码/档案，不自动push；不能先删prefix历史。第53轮62case仅作回归。

## 范围取自旧记录，不重新抽样

以`round6_bucket/results/main/rows_*.csv`中method=RA6逐case登记：30setting、1146case，1076非probe与70probe。CAIDA380、COD225、URL225、Shalla300、四原flow各4。完整seed0–4，flow seed0；原预算/查询生成器/10M参数/once和fresh/25%learning/75%cold tail不改。另登记MAWI24四预算（已见数据变体，不是新holdout）。

所有key使用第53轮v4 prepared raw bytes，原id/split/模型/prefix分数只读。COD/CAIDA数值8bytes、CAIDA-flow33bytes（128bit地址）、MAWI9bytes、URL/Shalla128bytes，超128bytes完全绕过，不截断不假称最长128。无成员索引/safe/cache_cost准备；hash仅bucket，不足以命中。完整key cache单owning数组、4-way CLOCK和第53轮物理计费保持。所有query包括static reject先查cache。

## 主结果、直接表图依赖

每case新执行以下10个主方法：Gama、Gama+10%、Replay(h权重全网格)、RA-stage1、RA-global、RA6-top3、RA6(top5)、RA6-top10、PlainBF、BF+Exact。14trees×13shares按新exact布局重新选择。无零树自动合并：t=0的BF明确作为对照，新零树变体在暂停的第54轮。

- 每case另测RA6、Replay、BF+Exact的**学习cache预热后**tail，不从cold计数推算；所有学习/查询成本单列。
- Learned stacked沿用其原negative/positive BF层定义（本来不使用prefix cache），也新执行learning选择及tail，以补本地Table`tab:main`右侧。它不被重命名为exact-cache方法；账单单列，不需成员验证索引。
- 原RA-stage1模型消融seed0–2（flow seed0）：noRepeat/noSA/noGT/mix0.5/mix1/global。closed-form Table变体另写exact布局适配：slot bit成本按完整key实际布局，最终cache取整数bucket；不调用旧prefix slot_bits或K._bytes。仍标为原closed-form思想的新exact实现，而非原prefix逐位相同代码。
- h权重hindsight：原seed0–2对全部h候选tail回放，非probe尾流相同；probe按原F-C用每个结构自身FP修改tail，单独报告。尾段oracle只能作诊断，不参与选择。
- 原seed0的完整RA加权候选预测/实测（含MAWI24每预算），只逐个构建/回放并立即释放，保存标量明细，不保留全部加权大数组。是Figure`motivation`/`holdout`数据基础，最优份额来自tail时明确hindsight。
- 原seeds1–4每case top10已构建候选的Stage1/桶预测及实测用于排名图；不重称独立holdout。全部低FP记录，按原>=30子集与全量并列，不追显著性。

## 计时与资源

- 重用固定模型/打分是本轮FP可比性的要求：load/tree准备/候选build/learning统计/selection/replay/FN逐项测；**不是从训练开始的construction**。选择时间另3rep专轮、完整构建和scalability后续新轮实现，未完成前不得称全文表图口径已经统一。
- 只共享不依赖流的候选网格；每case报告Replay独立搜索需承担的完整grid build测量（共享以节省本次总运行，不免费扣掉Replay构建）。RA stage1/top3/top5/top10共享预测表时分别累计本方法所需构建数和预测成本，不能用top10总time冒称top5。
- 只释放后续不使用的q_region工作区（第53轮等价已验证），不改变配置/BF/缓存/metadata；Learned stacked需要的结构不套该删除。
- 单worker/native1，RSS4GiB，磁盘至少4GiB、本轮新输出<=1GiB。单budget worker最多7200秒，整轮正式矩阵最多28800秒；超限保留失败停止，不自动扩大门限/删配置或重启内存失败。
- 固定pilot：URL64、CAIDA128的seed0 once/uniform-all/Zipf1-all（各3case），MAWI21/24KiB完整trace（1case）。共7case，不按结果换pilot。检查第53轮对应7方法树数/份额/FP/flags/cache SHA；所有方法新检查预算/FN。粗略按静态/流两类最大单case耗时推算1146成本，超过8h时暂停报告，不擅自缩减矩阵。

## 图表映射与边界

只读本地`paper/vldb/sections/*.tex`，未拿到用户具体PDF版的编号证书，不编译或修改论文。

- `tab:main`（本地实验章节第2表）：cold总FP＋warm/learned stacked→本轮。
- `tab:cases`（第3表）：配对比、topK与hindsight→本轮。
- `tab:ablation`（本地章节顺序第7表）、`tab:pred`→本轮原seed范围消融/排名。
- `fig:motivation`（引言Figure1）→本轮seed0全加权候选hindsight；`fig:cases`（按当前源文件顺序Figure4）、`fig:holdout`（Figure5）→本轮完整分布和MAWI24。
- `tab:cost`/`tab:e2e`/`fig:scal`：独立计时与全构建、100M学习流规模实验，**不由本轮已有FP时间冒充**，后续优先补齐。
- `fig:structure`、`fig:framework`是架构示意，不需重新测FP；后续写作需改缓存表述，本会话只记MD。

## 验收

完整1146＋4case清单；主方法矩阵无缺项、warm与stacked单列；原Gama无cache逐case回归；每次实体BF全member通过、最终cache对全原始member无命中且核验不改state；原14 GT19受影响统计配方保持；所有input/source SHA冻结前后相同。任何阶段仅完成子集不得宣称“主实验全跑完”。

# Round36：真实HTTP轨迹资格审计（不按方法效果筛数据）

2026-11-22。事前协议：目前只读取公开元数据及HTTP HEAD，未读取三个日志正文或运行候选模型。上一轮为round35；本轮不改变任何旧代码或论文。

## 目的和固定来源

审计两个自然工作负载：ClarkNet连续两周合并为**一个**工作负载；Saskatchewan七个月为另一个。不是三个独立数据集，也不是现代日志。两站公开条款允许再分发但要求限于广义流量分析；本研究不分析、关联或发布客户身份，不以host/IP作特征。

- https://ita.ee.lbl.gov/html/contrib/ClarkNet-HTTP.html
- https://ita.ee.lbl.gov/html/contrib/Sask-HTTP.html
- https://ita.ee.lbl.gov/traces/clarknet_access_log_Aug28.gz ：HEAD字节21756573。
- https://ita.ee.lbl.gov/traces/clarknet_access_log_Sep4.gz ：HEAD字节20751841。
- https://ita.ee.lbl.gov/traces/usask_access_log.gz ：HEAD字节30505430。

ClarkNet第一份网页链接日期与文件名不一致，以实际内容核验。Sask跨月；不得沿用round27“月份固定”的时间比较。解析支持标准CLF及元数据描述的ctime时间，按记录原顺序，不悄悄排序。键为GET完整request target bytes（保留querystring），只做词法特征，不访问这些URL。畸形/非GET/其他status计数单列，不输出原始行。

## 阶段A：下载，有限且不自动覆盖

每文件四块Range，每次下载使用新的独立空目录；三文件最多四个并发请求，全来自同一官方HTTPS站点。每块600秒超时，不自动重试/换镜像；Content-Range、长度严格检查，再按顺序组装，验证gzip CRC、压缩及解压SHA256。压缩总量73013844字节，解压流每文件上限512MiB。磁盘至少2GiB。任何失败保留partial和错误，下载未完整不得进入正式审计。

下载工具及本协议先冻结为download-freeze.json，下载期间可编写解析器；完整解析/模型诊断代码在首次读取日志内容前单独冻结。解析器单测仅用人工fixtures，不用实测日志修到得到有利结果。解析均使用python -I，代码与下载目录分离，不执行下载内容。

## 阶段B：固定数据语义与诊断

1. 全分发日志GET中200/304为success、404为absent；同key二者都出现则整体排除。**回溯稳定子集**，完整目录和冲突排除用到整个日志，不能冒充动态网站前瞻部署。
2. 前25%已解析GET序号为开发边界，边界先于状态过滤。另报告开发404后来成功、开发成功后来404、各类冲突请求数和404保留率。跨文件时间倒退、实际起止日期、每文件与逐月status计数必须保留。
3. 导出本地ignored NPZ：SHA256前64位key ID（检查有限集合碰撞）、round27同20项词法特征、标签、首次序号、稳定记录序列。不导出客户端身份或原始key；raw日志与逐key数组不发布。
4. 报告成员/负key/负请求规模、distinct比例、singleton比例、开发/尾段重复、共享完整特征向量数量。不得把cache miss或响应bytes为0当404。
5. 三固定种子3601/3602/3603；开发期已出现的负key按hash10%训练、10%验证，其余负key为学习/未来查询池；成员50%训练。固定16树/31叶/lr0.1/1线程LightGBM，不搜索模型。AUC只用于诊断：保留成员非训练半与开发negative validation，另报告尾段新key比例。不通过尾段FP或AUC选择模型。
6. 以negative validation score的20/40/60/80%分位数定义诊断region，重复边界去重。不是正式Gama/PLBF分区。只用学习期查询计算region重复度；报告各区支持数量，至少50个distinct负key的区才纳入重复度差异。
7. 记录下载、校验、解析/特征、训练、评分、诊断各阶段wall time与进程peak RSS；训练/准备成本不冒充查询延迟。

## 事前进入完整对照的工程门槛

这些是透明的工作量/数据资格筛查条件，不是算法保证或论文定理条件。**所有两个工作负载均完整报告，包括失败条件；不因RA胜负改变阈值。** 本轮不构建任何BF，不测RA或其他方法的FP。

- 稳定member >=10000；稳定negative keys >=1000；稳定404请求 >=10000；原404保留率 >=90%。
- 固定拆分后学习与尾段negative requests的三seed中位数均>=1000；训练/验证负key各>=20。
- 查询池负key中至少1%与某member具有相同完整20维特征向量。
- 开发诊断AUC三seed中位数>=0.70；学习重复比例中位数>=0.10。
- 至少两个诊断region各>=50 distinct learning负key，并且region重复比例max-min的三seed中位数>=0.10。

规模另列：稳定member>=50000才标注“达到更大目录门槛”。较小但通过基础门槛仍可作为补充真实工作负载；两个1995年日志都不能填补“现代工作负载”的缺口。未达到门槛不等于任何模型在此数据上无用，只表示不作为本次完整新对照的优先对象。

通过者再独立冻结后续五方法同预算对照（Gama、Replay、RA-global、RA-PLBF、BF+Cache）和固定模型/分区/cache的配对消融。预算由member规模和预设bits/member规则确定，不按尾段结果调；所有输赢留档。资格审计不能替代这两个效果实验，也不能预先保证发现正面结果。

# Round50：完整SIS文件开发诊断（完成，规模/split通过）

[协议](plan/design-freeze.md) · [冻结记录](plan/freeze.json)

第49轮全文件基本规模达标后，另立本轮，保留第48轮固定prefix失败。明确为已见完整文件规模后的探索，不是独立holdout，不修改旧窗口/标签/结果。

从只读inventory流式准备2749058members/3467negativekeys的20维原query词法特征；全source重扫只恢复稳定negative的真实顺序与GETordinal，不伪造重采样。全sourceSHA/行数/GET数须复现第49轮。所有原始key/输入矩阵保持ignored，不发布。

seeds5001–5003，原member50%train/earlynegative10%train10%val，固定16tree/31leaf/lr.1；检查样本量、开发AUC、1000score分段分辨率、特征重叠、learning重复、tail新key比例和cheap path支持规则。**不翻转score、不调class weights或训练比例来追AUC，不测方法FP。**

2项边界/身份fixture通过并冻结后启动；准备1800秒、每seed600秒、RSS4GiB，串行/单线程。offline原始key、矩阵、计数DB属于输入/训练工作区，不是免费Filter状态。16tree诊断不等于200tree完整候选网格的结论。

## 已完成结果

[开发报告](results/report.md) · [资格结果](results/qualification.json)

全轮216.09秒；prepared包含2749058members、3467negativekeys，完整63377条稳定negative请求的顺序与GETordinal复现第49轮。20维feature payload220202000B、rawkey blob350648199B属于offline输入工作区，不是Filter内存。

3seed负训练/验证key分别116/143、103/131、98/103，learning/tail规模全部通过。但原16tree开发AUC分别0.452/0.420/0.327，极不平衡训练下rawscore幅度巨大，约99.85%member在bin999。不能直接翻转AUC/score声称模型变好。

Seed5002的key-heldout划分移除了一个主要热点，learning/tail仅2819/5799请求，另外两seed约4.5万/1.7万；不能丢掉这个seed，也不能将三者当独立应用。所有下游方法必须在同seed用相同stream。

原结果保持，后续另立[第51轮训练稳定性开发消融](../round51_training_stability/README.md)，新配方不得追认给本轮。此轮尚无实体filter FP或SQL结论。论文未动，未push。

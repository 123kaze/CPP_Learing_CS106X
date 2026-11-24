# Round46v2：DNS观测响应资格审计（完成，但不合格）

[协议](plan/design-freeze.md) · [原body字节/字段映射核验](results/schema_verification.json) · [数据统计](results/data.json) · [资格结果](results/qualification.json)

公开MACCDC2012安全竞赛记录，**不是生产DNS流量**。原轮下载成功、因无#fields表头停止；本v2保留原失败，仅增加明确header适配并复用原资格代码。3项适配测试通过；原4项DNS语义测试保持。v2运行1.71秒，没有重下、没有修改原文件/源码。

公开分析笔记[字段汇总](https://github.com/cyberdefenders/MachineLearning/blob/master/Data_analysis/Network%20analysis/dns%20analysis.ipynb)的Git blob为`1b5753b07d813b172d463dc656bca6e3feea1882`。采用ts0/query8/qtype11/rcode13/answers20，并对每条记录核验qtype1对应A、rcode0对应NOERROR、rcode3对应NXDOMAIN。未使用的列不猜语义。新gzip仅加header，原62075487B body与SHA256逐字节一致。

## 结果

- 原记录427935条；A-query212477条。
- 其中189938条没有记录响应码，**不能当不存在**；另有42条SERVFAIL、220条REFUSED，同样不是negative。
- 观测NXDOMAIN21825次；过滤不支持名称和1个正负冲突name后，保留21733次，99.58%。
- 稳定NXDOMAIN域名1045个；稳定观测正域名只有**18个**。
- 记录顺序中A-query时间回退53693次，不能将其说成严格有序自然请求流。
- 开发AUC三seed约0.832/0.736/0.775、学习重复约90%；这些数字建立在极小正集合上，不能作为可靠模型部署证据。

唯一未过的事前规模门槛是`members>=1000`。**不调低门槛、不添加人工正域名、不进入五方法性能矩阵。** 18个成员本身就使简单精确集合/普通BF很有竞争力，不应为了展示AUC而声称需要学习模型。

## 语义限制

正类是观测A-query得到NOERROR且有answer，负类是观测NXDOMAIN；这是回溯稳定响应子集，不是独立验证过的全球DNS zone真值，也不覆盖TTL、动态注册、响应错误或中毒。规范化仅ASCII小写/去末尾dot，未解码转义名称明确排除；没有用IP/client/responsevalue作模型特征，没有反匿名化。

来源：[SecRepo目录](https://www.secrepo.com/maccdc2012/)、[MACCDC竞赛背景](https://www.netresec.com/?page=MACCDC)。SecRepo默认许可说明适用于其生成/托管材料、底层PCAP许可未独立确定；本artifact仅发布代码/聚合/哈希，不发布原始qname/client数据。没有论文修改或自动push。

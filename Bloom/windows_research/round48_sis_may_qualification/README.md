# Round48：SIS五月固定前缀资格审计（完成，未通过门槛）

来源：[Charles University真实线上SIS日志](https://zenodo.org/records/3241445)，CC BY4.0；2018年5–11月Combined Log Format。原身份/参数匿名化细节有限，原始日志不发布，client/userID/referrer/UA不作特征。

[预声明](plan/design-freeze.md) · [提取源码冻结](plan/extract-freeze.json)

## 当前阶段

完整3GBarchive下载已校验，实际944.04秒。归档共207187586686B展开数据，**不整体解压**。原定五月文件13687894566B约12.75GiB，超过原12GiB门限；用户明确允许提高到16GiB，其余RSS4GiB/单线程/保留8GiB磁盘/1200秒上限不变。

原单线程提取达到1200秒上限后停止，TimeoutError与670424758B部分文件保留，未用于解析。用户随后明确授权最多4线程/8小时；另立[提取v2](../round48_sis_extract_v2/README.md)，同一五月文件写入另一个新空目录，不resume/拼接旧partial。官方MD5仍需匹配`dee4c55d036d6d1768a6f26a15b834c4`；RSS4GiB/输出16GiB/保留8GiB空间限制不变，超限不自动重试。

提取v2已完整完成，官方MD5及完整SHA256通过，耗时7356.89秒，峰值RSS低于4GiB。HTTP解析的5项人工fixture测试通过，完整资格源码与该输入SHA在首次读取真实HTTP记录之前另冻。固定前2000000行审计现已完成，运行120.86秒（含哈希与阶段检查），[完整报告](results/report.md)与[独立复核](../../docs/round48_evidence_20261123/verification.json)均已保存。

## 资格不是预设RA获胜

任务仅是observed200/304target与404target的回溯稳定子集；200登录页/应用错误不能证明业务record存在。认证/redirect/5xx不当negative。完整target含querystring，冲突key排除并计保留率；不看方法FP后换月、改窗口或改门槛。

预设members>=10000、negativekeys>=1000、稳定404>=10000及保留>=90%，各seed训练/验证/learning/tail规模门限固定；AUC、特征重叠、重复差和cheap path支持规则均先诊断。只有资格成立后，才考虑另冻五方法/完整成本实验。

## 本次资格结果

- 固定前200万原始行共653207993B，解析1946580个GET；实际时间2018-05-23 04:32:03至12:33:25（+0200），回退144次。**五月文件的这一记录前缀不是月初或整月代表性保证。**
- observed-success稳定keys140493，404稳定keys仅211；404请求9940，0冲突、100%保留。
- 因negativekeys<1000、404requests<10000，以及各seed负训练/验证keys不足20而不合格。训练/验证key数分别13/8、3/10、7/6。
- 开发AUC约0.012/0.123/0.140，但负验证集合过小，不据此对整个业务的可学习性下结论；也不倒转score/标签把它改成有利AUC。
- learning重复比例约96.8%–97.1%，精确特征重叠约20%；多次请求不等于足够多独立负key。first/two-components支持规则只排除极少数负请求，不解释全部负例。
- 没有把9940四舍五入判为10000，没有降低门槛、扩大prefix或改选月份；**没有运行五方法FP或SQL时延矩阵，因此既不能说RA赢，也不能说RA在该任务已输。**

完整五月文件已安全保留。后续另立[第49轮全文件规模清点](../round49_sis_inventory/plan/design-freeze.md)，明确是看过本prefix之后的新探索，不覆盖本记录、不冒称第48轮通过，也不是新的独立holdout；只清点完整文件，不训练或测方法FP。论文未动，未自动push；本轮资格任务已结束。

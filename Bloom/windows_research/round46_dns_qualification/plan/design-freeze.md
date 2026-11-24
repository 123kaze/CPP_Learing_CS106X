# Round46：MACCDC2012 DNS响应语义资格审计

2026-11-23。继续探索真实观测响应，不保证获得正结果。此轮先数据资格/AUC，不测方法FP；若合格另冻方法比较。**MACCDC2012是安全竞赛/实验环境记录，不是自然生产DNS负载**。即使正结果也要保留这个标签，不能写成一般生产需要RA。

## 来源/下载

公开https://www.secrepo.com/maccdc2012/dns.log.gz，HEAD:6606969B，ETag\"64d079-503965768af73\"，last-modified2014-09-21。MACCDC竞赛来源另由Netresec页面核验。SecRepo声明自己生成/托管的数据默认CC BY4.0、例外另注；目录未见单文件例外，但底层PCAP许可未单独确定。本轮仅下载公开衍生DNS日志做本地研究，不再发布原始域名/客户端数据、不下载或执行恶意样本，不绕过访问限制。

下载到新空inputs/source目录，HTTPS、If-Match固定ETag、最多120秒/10MiB、无重试。验证长度、SHA256、gzip CRC；展开最多256MiB，不写入可执行目录、不执行内容。脚本src与数据分开，Python -I。

## DNS任务定义

读取Zeek/Bro text日志#fields描述，严格tab分隔，必须具备ts/query/qtype/rcode/answers。只保留qtype=1(A)查询，避免A/AAAA类别捷径。query转ASCII小写并去一个末尾dot作为DNS规范化身份；空名/root或包含未解码\\x转义/非ASCII/控制字符记录为不支持并排除计数，不静默改成另一个名称。原IP/client/uid/answers内容不保留。

在可解析A-query ordinal上先定前25%development/learning边界，不按标签重排。rcode=3为观测NXDOMAIN；rcode=0且answers非空为观测可解析；NOERROR无答案(NODATA)、SERVFAIL/REFUSED/未知/缺响应均不推断nonmember，另计。

同一规范qname出现上述正/负冲突时整体排除，记录比例。剩余正qname构成静态观测目录，负qname构成观测NXDOMAIN池。**这是回溯稳定响应子集，不是全局实时DNS zone快照；动态DNS更新、毒化/错误响应、TTL或未来新域名不在静态0FN保证范围内。**原请求顺序不改，不人为注入或增加NXDOMAIN重复。

## 查询特征、split与资格

32维固定query-only特征：round44固定24词法特征＋label数/最长label/平均label长度/Shannon字节熵/后缀.com/.net/.org/punycode标记。只用qname，不用rcode/answer/IP/timestamp/qtype变化/未来频率。原SHA256前64bits仅作旧BF哈希输入，准备时有限集合唯一性assert；后续严格cache若运行必须存完整原始规范化qname，不把hash当精确key。

seeds4601/4602/4603，member随机半数train；只从前25%首次出现负key按独立hash10%train/10%val，余下query池；相同name跨split互斥。固定16tree/31leaf/lr.1/单线程开发诊断，heldout members+neg_val AUC。特征重叠、学习重复、neg_val分位score-regions重复差全部报告。

进入后续五方法比较的门限（不是按RA效果）：静态members>=1000、negative keys>=1000、保留NXDOMAIN请求>=10000、冲突排除后NXDOMAIN保留>=90%；每seedtrain/val负keys>=20、learning/tail评估negative各>=1000。AUC>=.70、特征重叠>=.01、学习重复>=.10、至少两区各50distinct且gap>=.10只作解释flag，不因flag差而删除规模合格控制。若门限失败，记录不合格、不调低门槛、不自动重下/扩展数据。

## 执行记录

fixture测试和所有解析/诊断源码在首次下载/解析前冻结；原环境单线程，无C++本地构建；单流程600秒，至少2GiB磁盘；保存下载/解析/诊断耗时、来源hash/计数/失败，不公开原始域名或客户端。此轮不改论文、不push、不修改旧冻结轮次。

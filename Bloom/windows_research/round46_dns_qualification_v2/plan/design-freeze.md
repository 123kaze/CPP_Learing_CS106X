# Round46v2：明确headerless DNS字段映射，仅修格式适配

2026-11-23。原round46下载成功（6606969B、gzipCRC通过、展开62075487B），解析首记录因MissingZeek#fields停止；旧源/失败日志不修改，不重新下载。

只读首记录结构：23个tab分隔字段，无#fields。公开分析笔记https://github.com/cyberdefenders/MachineLearning/blob/master/Data_analysis/Network%20analysis/dns%20analysis.ipynb，Git blob1b5753b07d813b172d463dc656bca6e3feea1882的DataQualityReport给出23列顺序（427935条记录）。该笔记未直接提供raw读取schema，故同时要求本数据每条记录的实际数值/名称一致性检查，不只凭列位置猜。

采用0-based ts0/query8/qtype11/qtype_name12/rcode13/rcode_name14/answers20；其余字段名用unused_N，不赋予不需要/不确定的含义。每条原记录必须恰好23列；qtype1时qtype_name必须A；rcode0必须NOERROR、rcode3必须NXDOMAIN，其他rcode也不推断不存在。任何不一致停止留档。

在新的ignored cache目录生成derivedgzip：只加一行明确#fields，其余所有原始记录字节、顺序不变；写headerless原bodySHA核对原下载uncompressed SHA，输出bodyhash/长度/行数，不输出原qname/client。这不是原文件已存在schema的伪装，而是明确的格式适配。原audit46.parse/diagnose函数复用，只将其输出ROOT绑定到本新轮目录；旧文件不改，不执行旧fetch/check。

原round46成员/负key定义、A-only、规范化、冲突排除、32query-only特征、split、门槛完全不变；所有源码/原下载/原失败/原plan哈希冻结后执行。未测方法FP，不调资格阈值。下载9.65秒属于原轮，派生/解析/诊断时间本轮另计。若不合格，记录不合格，不继续开五方法矩阵。

MACCDC2012是竞赛/实验环境，不是生产DNS。观测rcode不等于已验证全局zone真值；回溯静态子集不代表动态DNS安全部署。原始域名/client不发布，源码数据隔离Python-I；无论文修改、push或重启原失败轮次。

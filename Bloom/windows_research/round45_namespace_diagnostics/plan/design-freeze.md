# Round45：命名空间/原key size表示的开发段探索

2026-11-23。已用过的cluster001–003上进行明确的事后探索；不看新tail方法结果，不声称新独立验证。下载新cluster004–006之前必须另立后续冻结，本轮绝不读取它们。

固定seeds4401/4402/4403，沿用round44前25%GET成员目录、后25%learning与hash-key train/val互斥规则。只用heldout members+negative validation测开发AUC，训练member_train+negative_train；固定16tree/31leaf/lr.1/单线程，原24维AUC须逐seed复现qualification记录。

四个预设表示：lexical24；lexical24+query original key_size；lexical24+prefix64onehots；二者合并89dims。只用key_size列，不读response value_size/TTL/clientid作为特征。原key_size由请求提供，生产原key存在时可直接求长度；本匿名数据若用于后续在线计时，需要显式传入这个query metadata，不能借全局key映射免费查特征。

Prefix长度1/2/4/8，每长度选训练distinct keys最常见16个prefix，按count降序、bytes字典序tie-break。不用validation/tail key建立词表，不解析匿名hash数值语义，不反匿名化。没有长度达到n的key不匹配该组。固定64维onehot，未用槽填0；矩阵顺序固定。词表单一owning uint8array：32byte header，各组16slots，每slot一个valid byte+n个完整prefix bytes；总payload336B，计ndarray header（本env112B）共448B。无外部词表指针。发布仅词表hash/字节/有效槽数，不输出literal prefix。

开发闸门事前固定：至少2/3cluster的3seed中位“combinedAUC−lexicalAUC”>=.03且combinedAUC中位>=.65。若不通过，停止这个特征分支、留档，不调整阈值或开新数据找赢家。若通过，冻结合并表示+完整词表计费后才在cluster004–006独立验证；开发通过不是RA的FP/端到端胜出。

每个cluster只读取原文件GET前半段，恢复original key_size并核对原prepared trace/key bytes；不重解析尾段或运行BF。4representation×3seed×3cluster=36models，分项记录元数据恢复、词表/特征、训练、score、AUC及key交集检查；每cluster600s，三个顺序worker，不重试。完整来源/脚本hash冻结，输出拒绝覆盖，旧round44失败与reportv2均不改。没有论文修改或push。

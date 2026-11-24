# Round49：整份已校验五月日志规模清点（新的探索，不修写第48轮）

2026-11-23。用户持续要求探索真实场景；第48轮固定前2000000行未通过资格（140493member/211negativekeys/9940个404）。该结论和固定窗口保持，不降低或倒填门槛。

本轮明确是**看过初始prefix后的探索性全文件inventory**，不是独立holdout或第48轮复试。为了避免按效果挑窗口，只扫描完整已校验sis-log-201805-anonymous.txt至EOF，不选择日期子段，不读取其他月份。不训练模型、不计算方法FP、不优化特征/预算，故没有“RA已经胜出”的结论。

## 不变输入和语义

固定完整五月文件13687894566B，官方MD5dee4c55d036d6d1768a6f26a15b834c4，SHA2563ed4938ba75825e31790e6379f563d6a59aee9d36d600ce8cab22bcaa331a414。只GET，200/304为observed-success、404为observed-missing，其他状态/方法另计；同完整target（含querystring）正/404冲突整体排除。保持源记录顺序，不排序。依然是HTTP响应观察，不是业务record存在性证明；全文件回溯稳定目录有前瞻部署限制。

复用原已冻结data36.decode_line，仅改为完整扫描并用磁盘SQLite做精确key计数，不保留全流和巨大Python key字典。SQLite只作为离线清点工作区，**不是应用后端计时/部署结果**。

## 有界实现

新空ignored cache目录，keys表BLOB PRIMARY KEY、flags/first_GET_order/last_GET_order/success_count/404_count，WITHOUT ROWID；每10000条输入最多一个内存聚合batch，参数化SQL，不执行URL。事务批量更新、SQLitecache64MiB、journal/sync OFF仅用于可重建离线工作区；源数据始终保留，partialDB不当完整结果。

单进程/单线程，wall1800秒、RSS4GiB、DB文件8GiB上限、至少8GiB磁盘余量；每30秒进度checkpoint，超限停止留档，不自动重启。原始client/userID/referrer/UA不保存；原target只在ignored DB中，报告仅聚合/hash，代码放src、Python-I。

在恰好第2000000行，对已计入数据做SQL聚合，与第48轮rawGET/status/member/negative/404/conflict/prefixSHA逐项复现，验证新统计实现未悄悄改变旧窗口语义，然后继续至EOF。最终全文件SHA须匹配提取回执。最终记录全文件行数/GET数、日期/时区范围及逐日期状态聚合、时间回退、distinct member/negative/conflict、404保留率、各key频数分布摘要，不输出raw key/client。

对原规模标准members>=10000、negativekeys>=1000、稳定404>=10000、保留>=90%只报告全文件是否满足；**这不是完整资格**，训练/验证key规模、前瞻split、可学习性/简单规则与后端成本仍未测，不能直接开始或宣布正式方法胜出。如果需要后续研究，必须另冻其协议并披露本全月扫描已发生，不称未看过的独立数据。

原第48轮完整失败资格、原解压timeout及partial保留。无新下载、无编译、不改论文、不push。

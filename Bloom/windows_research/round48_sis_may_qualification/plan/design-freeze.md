# Round48：预选五月线上日志的提取与资格审计

2026-11-23。接续已完整校验的SIS archive。用户明确允许将五月输出上限从12GiB提高到16GiB，其他限制不变；原gate失败保留。没有换月份或科学标准。

## 提取阶段（先于任何原始日志解析）

预选sis-log-201805-anonymous.txt，归档list显示13687894566B，官方manifest MD5=dee4c55d036d6d1768a6f26a15b834c4。archive2995604801B，SHA256=c20332ec19b8679873ee88e26264ae15bd5dfad0a71e8e1557be95bc45752f4a。使用原round47项目内已校验的arm64 zpaq工具，无编译/系统安装。

只提取该确切文件到本轮新空cache/may目录，显式-to完整目标路径，-threads1，不-force，不执行archive文件。输出最多16GiB、RSS<=4GiB、wall1200秒、至少保留8GiB空闲；监控仅子进程/本轮目标，超限terminate并记录，不自动重启。必须核验最终长度/MD5，另存SHA256，再进入解析。其他月份不提取/解析。

## 初次资格范围（解析源码必须首次解析前再冻结）

仅读五月文件前2000000条原始行，若EOF更早则全文件；该固定prefix不是完整五月，更不是七个月全数据。保持文件记录顺序，记录timestamp范围/回退，不因稀少404扩窗或换月。

按combined log解析，只取GET，完整request target bytes含query string保持。状态200/304作observed-success、404作observed-missing；redirect/auth401/403/5xx/其他状态单独计数，不当negative。任一key在固定prefix中同时出现success/404则整体排除，记录冲突及404保留率。成员目录为回溯稳定observed-success集合，不从状态码推出真实业务record存在性；200登录页/应用错误与业务结果无法从access log辨别，明确语义限制。

前25%成功解析GET ordinal作为development/learning边界，在状态筛选/冲突排除前确定。seeds4801/4802/4803；member半数train，early negative key哈希10%train/10%val，其余query pool，key互斥。固定16tree/31leaf/lr.1开发诊断；不运行方法FP前先判门限。

门限沿round47预声明：members>=10000、negative keys>=1000、稳定404requests>=10000、404保留>=90%；每seed负train/val>=20、learning/tail评估negative各>=1000。AUC/精确特征重叠/learning重复/至少两score区域各50distinct的重复差作解释diagnostic，不按tail方法效果选择。

query-only特征先采用旧round27的20维原始target词法特征，无status/client/userid/referrer/useragent/未来频率。Cheap-rule诊断：仅依据member目录已有的第一/前二个path components支持，可拒绝多少negative；若cheap支持规则已能排除大部分负查询，不把可学性直接解释为需要树模型。规则存储成本需另列，诊断不冒充已计时优化实现。

## 隐私和资源

不输出raw log、用户/IP、查询参数或原始target值；只保存ignored prepared arrays、聚合计数/hash。解析脚本与数据隔离、Python-I，单线程；固定line64KiB上限、解析180秒、诊断每seed120秒，RSS4GiB以内后验核验，不并行大worker。不能为正结果更改source/窗口/阈值。若不合格，留档停止此数据分支，不跑低意义性能矩阵。

数据许可CC BY4.0，保留来源/作者/许可及变换说明，但原始数据不发布。本轮不改论文、不push、不承诺RA胜出。

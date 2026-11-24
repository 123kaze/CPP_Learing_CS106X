# May extraction v2：用户授权4threads/8hours，科学输入不变

2026-11-23。原round48单线程提取达到1200秒上限后停止，错误为TimeoutError，原部分文件逻辑670424758B，未核验/未用于解析，子进程已清理。原代码、部分文件和失败日志保持。

用户明确选择“最多4线程、8小时”。新v2仅提高解压线程/时间：threads4、wall28800秒；仍仅指定sis-log-201805-anonymous.txt，预期13687894566B、MD5dee4c55d036d6d1768a6f26a15b834c4；输出最多16GiB、RSS4GiB、至少保留8GiB空闲。数据来源/五月选择/前2000000行资格窗口/模型特征/科学门限不变，不能因此保证正结果。

复用原校验过的项目内预编译zpaq，不安装/编译、不重下archive。新输出在本轮独立新空cache/may目录，不resume/拼接旧partial，不-force，不提取其他月份，不执行archive内容。完整tool/fileSHA、原downloadreceipt和旧failure作为输入冻结。

每秒只监控当前子进程RSS/输出size/磁盘/elapsed，30秒保存一次资源进度（逻辑size、分配bytes不是checksum成功进度），超限terminate并写失败；无自动retry。失败也保存wall/observedRSS/partialsize，避免旧失败缺少资源分项。成功必须返回0、恰好一个指定普通文件、长度/官方MD5/SHA通过；然后才能把新文件交给尚未冻结/执行的资格parser，不能把旧round48提取改写成成功。

提取性能仅是数据接入成本，4线程不适用于方法实验；后续模型/选择/回放仍单线程。论文未动，本批不push。

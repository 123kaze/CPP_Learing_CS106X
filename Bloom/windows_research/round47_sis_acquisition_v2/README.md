# SIS接入v2：完整下载已校验，五月提取转入第48轮

[资源协议](plan/design-freeze.md) · [冻结记录](plan/freeze.json)

用户在得知原4MiB探针约0.20MiB/s、完整包单速预计约4小时后，明确选择“允许后台最多6小时”。四个预设range已全部下载并核验，完整2995604801B包于944.04秒完成（约15.7分钟），未重试。实际吞吐优于小探针的保守估计，不能把原估计当实际耗时。

原round47的1800秒门限失败、4MiB完整探针以及预编译工具验证均保持。没有改变数据/月选择或科学门槛，没有本地编译/全局工具安装。

每块HTTP206/Content-Range/长度/SHA通过；官方MD5`8a48f22d0df19fb8d5044e54b66aac6e`匹配，完整SHA256为`c20332ec19b8679873ee88e26264ae15bd5dfad0a71e8e1557be95bc45752f4a`。[下载回执](results/downloads.json)的status=verified；没有拿partial作正式输入。

单线程归档list已完成（2.526秒）：全部七个月展开207187586686B，不整体提取。预选五月13687894566B（约12.75GiB），超原12GiB门限，原[gate记录](results/extraction_gate.json)保留。用户明确允许五月输出上限提高到16GiB，另立[第48轮](../round48_sis_may_qualification/plan/design-freeze.md)。其单线程提取达到1200秒上限后停止，部分文件未用于解析；用户随后明确授权[提取v2](../round48_sis_extract_v2/README.md)最多4线程/8小时，其他内存/磁盘限制不变。首次解析前另冻解析源码，六月等其他月未提取/解析。

此时没有该日志的资格诊断、AUC、方法FP或部署结果；不预告正结果。数据来自真实线上系统，但404/认证/动态URL语义尚需核验。论文未动，原始数据/二进制工具不发布，本批不自动push。

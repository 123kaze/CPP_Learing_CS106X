# Round47：真实线上SIS数据接入（工具成功，网络资源门限未过）

[协议](plan/design-freeze.md) · [本地预编译工具核验](results/tool.json) · [Range探针](results/network_probe.json) · [网络门限](results/network_gate.json) · [停止记录](results/download_failure.json)

用户明确授权3GB真实线上日志与隔离目录的预编译ZPAQ工具，不本地编译、不改系统。

## 已完成

- Homebrew zpaq7.15 revision1 arm64_sequoia bottle，SHA256验证通过；只提取bin/zpaq到本轮tools目录，Mach-O arm64和只依赖系统libc++/libSystem核验，帮助输出版本正确。
- 没有brew/system安装，没有源代码编译，没有执行数据包里的内容。工具binary不发布。
- 3项range边界/HTTP校验单测通过。
- 官方Zenodo archive的首4MiB完整HTTP206 range验证通过，Content-Range/长度/SHA保存，真实body传输19.964701秒，连接至首字节1.054240秒。

## 按冻结规则停止

按单探针body吞吐保守估算完整2995604801B传输约14263秒（约3.96小时），超过事前1800秒上限。**未启动四块大包下载，未组装/解压/解析该数据，不使用partial作为实验数据，也没有自动重试。**

已明确授权的数据来源/工具不等于自动延长资源上限；若用户愿意后台等待更久，需要另立只改下载时间上限的接入v2，保留本次网络门限失败记录和固定五月选择，不动科学判定门槛，不换更有利月份。

## 数据价值仍待核验

来源：[Charles University SIS 2018线上日志](https://zenodo.org/records/3241445)，CC BY4.0，Combined Log Format提供METHOD/path/status等。原archive MD5由官方API给出，内部七个月文件由.md5sum提供。原始路径参数匿名化、身份/认证/业务错误语义及真正404规模未知；“真实线上来源”不保证RA会赢，也不等同于KV存在性实测。

六月及其他月份未打开；本轮工具/网络探针不是任何算法正结果。论文未动，本批未push。

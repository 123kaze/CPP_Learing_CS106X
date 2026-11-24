# 五月提取v2：完整提取并通过官方MD5（已完成）

[协议](plan/design-freeze.md) · [冻结记录](plan/freeze.json)

原round48单线程提取达到20分钟上限后停止，仅写出670424758B；旧部分文件和TimeoutError留档，不用于实验。用户随后明确选择“最多4线程、8小时”。

本轮重新提取同一个五月文件到独立新空cache/may目录，不拼接/恢复旧partial。仍是13687894566B、官方MD5`dee4c55d036d6d1768a6f26a15b834c4`。完整archive及tool无需重新下载；没有本地编译或系统安装。

限制：4threads、28800seconds、RSS4GiB、output16GiB、至少8GiB磁盘空闲。每30秒保存资源checkpoint；逻辑文件长度或allocated bytes不等于内容已校验。只有`results/extraction.json`的status=verified且官方MD5匹配，才算完成。任何超限或失败停止，不自动重试。

精确文件到精确目标、四线程和不覆盖的fixture通过。实际提取及校验7356.89秒（约2小时3分钟），观测峰值RSS3958898688B，低于4GiB；最终13687894566B、官方MD5匹配，SHA256为`3ed4938ba75825e31790e6379f563d6a59aee9d36d600ce8cab22bcaa331a414`，见[完整回执](results/extraction.json)。没有复用旧partial，没有提取其他月份。

五月数据现在可交给原round48资格parser；该parser源码和完整输入SHA在首次HTTP解析前另冻，固定前2000000行，不改变科学协议。提取成功本身不是数据资格或方法胜出的证明。

本轮4线程只用于数据解压，后续模型/方法实验仍单线程。论文未动，未push。

# Round36：真实HTTP轨迹资格审计（已完成并核验）

[完整报告](results/report.md) · [核验记录](results/verification.json) · [下载回执](results/downloads.json)

**ClarkNet通过全部事前工程门槛，Saskatchewan未通过404保留率门槛。** 两个工作负载均完整报告，没有按RA胜负筛选。

| 工作负载 | 稳定成员 | 负key | 稳定404请求 | 404保留率 | 开发AUC中位数 | 查询池特征重叠 | region重复比例差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ClarkNet | 32581 | 6834 | 66484 | 95.19% | 0.7990 | 44.59% | 0.4475 |
| Saskatchewan | 18869 | 4348 | 18311 | 89.00% | 0.9687 | 21.47% | 0.1460 |

Saskatchewan未达到事前90%保留率，不降低门槛使其通过。ClarkNet虽比NASA目录大，但仍未达到另列的50000成员门槛；AUC、重叠与重复差都不是方法效果证据。后续仅对ClarkNet另立冻结对照。

实际格式均为CLF；Saskatchewan日志时区为**-0600**，不同于网页文档的-0400，解析采用行内时区。ClarkNet实际3328632行，比网页所列3328587多45行；报告保留实际文件计数，不按网页强行删行。原始顺序时间回退1130/200次，不静默排序。

本轮先审计ClarkNet两周合并日志和Saskatchewan七个月日志，不依据RA相对胜负筛数据。它们都是1995年日志，不能声称填补现代工作负载缺口。

- [事前协议与工程门槛](plan/design-freeze.md)
- [下载冻结](plan/download-freeze.json)、[解析及诊断冻结](plan/freeze.json)
- 三份官方HTTPS日志，共73013844压缩字节；固定四块Range／文件，最多四并发，单块600秒，无自动重试。
- 六项人工fixture单测通过，涵盖CLF/ctime格式、跨月时间、静态冲突排除、零字节200非404、按key时间拆分、AUC及固定模型region计数、资格判据不读取方法FP。
- 下载完成并验证CRC/SHA后，才用已冻结解析器检查规模、自然404重复、特征重叠、开发AUC与region重复差；全部两个工作负载均报告。

## 数据与结果边界

真实HTTP status用于任务标签；不使用客户端host/IP、status、响应大小、时间或频率作模型输入。原始日志、request targets和逐key缓存数组不发布。每次下载放在独立空目录，解析用`python -I`，不执行下载内容。

稳定成员目录和冲突排除使用整个分发日志，这是**回溯稳定子集**而非动态网站前瞻部署。报告开发404后来成功、开发成功后来404以及被排除请求的比例，不隐瞒时间变化。

本轮不构建BF，不测五方法FP。固定16树诊断的region是开发验证分数分位区间，不是正式Gama/PLBF分区。资格通过不等于模型比BF更划算，更不等于重加权单独有效。

## 执行

```sh
.condaenv/bin/python -I windows_research/round36_http_qualification/src/test36.py
# 下载和审计均拒绝覆盖；不要在已有运行目录重复执行。
.condaenv/bin/python -I -u windows_research/round36_http_qualification/src/fetch36.py
.condaenv/bin/python -I -u windows_research/round36_http_qualification/src/run36.py
```

通过资格的候选另立新轮次，冻结五方法同预算对照及固定配置配对消融；所有负面结果保留。不修改论文、不改任何旧轮次，也不自动推送新结果。

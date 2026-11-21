# Round27：真实HTTP缺失资源查询

**已完成并核验：两份NASA日志、3个split/hash seed、3个预算、5种方法，共90行结果。**

- [冻结协议](plan/design-freeze.md)
- [完整报告](results/report.md)
- [逐方法数据](results/rows.csv)
- [数据和AUC诊断](results/datasets.csv)
- [各区域真实重复性](results/region_repetition.csv)
- [完成记录](results/completion.json)、[核验记录](results/verification.json)

## 不是协议字段造出来的优势，但也没有战胜BF+Cache

模型只看20个路径/URL字节统计特征，没有HTTP状态码、响应大小、请求频率或时间。16树的held-out AUC约0.862–0.901；每个测试池有约300–350个负key与成员共享完全相同的特征向量。404请求的真实重复顺序保留，不合成Zipf。

4/8KiB四个“月份×预算”设置，RA-PLBF相对Replay的逐seed平滑比值中位数约0.815、0.626、0.738、0.566；相对RA-global也有改善。因此这里观察到**不依赖UDP/TCP标签、且并非仅比较“有／无缓存”**的完整RA-PLBF改进。但树数、缓存份额和精排也可能不同，不能单凭此表将因果全部归于重加权；固定分区的机制隔离另见第28轮。

**但是，同预算BF+Cache明显更好**：上述四设置RA/BF+Cache约3.46、3.63、4.11、3.27。16KiB多数接近零FP，没有足够辨识力。这个试验不能证明学习模型整体优于无模型方案，反而提示小成员集合/小缺失工作集下，模型和导航开销不划算。没有为了得到正结果而换预算、裁剪seed或隐藏BF基线。

## 数据范围与系统边界

原始数据：[Internet Traffic Archive NASA-HTTP](https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html)。八月下载镜像：[COM6012/ScalableML](https://github.com/COM6012/ScalableML/blob/master/Data/NASA_access_log_Aug95.gz)。直接下载两次超时后，同URL的4分块续传成功，拼接长度和gzip CRC验证通过；下载receipt保留每块和全文件SHA256。

**“完整”指完整的分发gzip，不是完整日历月：** 七月实际GET时间范围为1995-07-01 00:00:01至1995-07-28 13:32:25；八月至1995-08-31 23:59:53。七月1891715行、八月1569898行；不能照来源网页笼统写成完整七月31天。八月记录顺序有1处时间回退，按冻结协议保留原记录顺序，而非事后重排。具体起止时间、排除数均在`data_*_preparation.json`。

成员目录由完整分发日志中的200/304资源构建；出现成功和404冲突的资源剔除。**这是回溯构造的静态稳定子集**，不是前瞻性的动态资源发现实验。训练/验证负key必须在学习边界前出现、与测试负key不重合，但完整成员目录和冲突剔除使用了整份数据，这一限制不能省略。

- 成员7110/6464，稳定负key2279/1663；原始稳定404请求10575/9872。
- 查询执行是标签驱动的静态trace模拟，**不声称是真实HTTP后端或SQL交错端到端计时**。
- 主方案含预算外成员hash验证索引；同预算仅指Filter Budget，不把后端全量资源计为零。
- 全成员BF/Cache检查为0FN，所有90行物理总字节不超过预算。
- 训练、评分、索引、选择和回放均记录墙钟时间，但并非受控多次端到端延迟实验。

## 复核

从`Bloom/`运行：

```sh
.condaenv/bin/python -I windows_research/round27_http_real/src/test27.py
.condaenv/bin/python -I windows_research/round27_http_real/src/report27.py
```

3项单测通过。正式执行器拒绝覆盖；输入、预处理缓存不提交。原始下载失败的partial保留在忽略目录，不用作正式数据。

**尚未填平的研究缺口：** 仍需更大、现代、具有真实重复与非平凡特征区分的工作负载，才能进一步检验学习模型本身是否值得占用内存。这不是通过本实验得出的正面结论。

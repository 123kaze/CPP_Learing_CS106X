# Round28：Proposition 5.3 的受控机制验证

**已完成：168 组配对设置、504 次物理 BF 构建。**

论文基准是 `paper.git` 远端 `main` 的 `e256658`，文件 `vldb/sections/analysis.tex`，命题 `prop:gain`。不是本地旧 `paper/submission-sync` 或根目录 `sections/`。

- [冻结协议](plan/design-freeze.md)
- [完整结果及适用边界](results/report.md)
- [交互散点图与全部数据表](results/interactive.html)
- [可绘制行 CSV](results/scatter_rows.csv)
- [源码冻结](plan/freeze.json)、[完成记录](results/completion.json)、[独立结果核验](results/verification.json)

## 做了什么

URL 固定16树、TCP-only 固定1树，分区保持不变；区域总查询概率不变，只改变区域内负 key 的集中程度。比较同样 BF 位预算下的验证权重 `h`、论文原始 Che 权重 `M(T)`、精确有限窗口 TTL 权重。使用相同请求和 BF 哈希种子配对。

分别报告：
1. 外生 T、两种连续分配均未截断；
2. 存在 FPR=1 截断；
3. 真实固定2048字节的 CLOCK，T 不再外生。

**TTL 的内存不受容量约束，不能拿它冒充同内存系统对比；同内存对比看 CLOCK。** 这是真实特征上的受控合成查询，不是新真实工作负载。

## 结果不是“普遍验证成功”

- 117/168设置满足两种分配都内点，连续目标的 AM/GM 因子误差小于核验容差；51组涉及截断。
- 论文权重下，TCP-only 的预测收益与实测 TTL 收益呈较强的描述性关联，内点组 Spearman≈0.718；URL 只有≈0.121，不能说两数据集都稳定贴合理论。
- 全部84组/数据集、论文权重、CLOCK：URL为57胜2平25负，TCP-only为74胜0平10负。不能当独立样本做显著性结论。
- 低FP分母、有限key、BF位数/探针数离散化及缓存耦合会造成明显偏离，全部负收益点保留。

## 运行

从 `Bloom/`：

```sh
.condaenv/bin/python -I windows_research/round28_reweight_mechanism/src/test28.py
.condaenv/bin/python -I windows_research/round28_reweight_mechanism/src/report28.py
```

5项单测包括独立SLSQP解、有限IID序列枚举验证TTL期望、区域流量不变和物理BF/CLOCK正确性。正式结果已存在；`run28.py` 拒绝覆盖。再次实验必须新目录/新协议，不修改冻结源文件。

图采用形状区分数据集的黑白设计，含浅/深色 PNG、PDF；实际PNG已渲染检查，HTML脚本经过语法检查。没有声称交互页面已在浏览器自动化测试。

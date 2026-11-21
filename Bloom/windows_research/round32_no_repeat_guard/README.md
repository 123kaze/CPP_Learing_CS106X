# Round32：RA6-NR32显式无重复路径

**已完成并独立核验：原140个无重复案例全部匹配Gama与原RA6的FP；4个重复控制全部匹配原RA6。**

- [冻结协议](plan/design-freeze.md)
- [完整结果、保证论证与边界](results/report.md)
- [逐案例与计时](results/rows.csv)
- [完成记录](results/completion.json)、[核验记录](results/verification.json)
- [实现](src/guard32.py)

## 真正修了什么

这是单独命名的事后新变体，不改原RA6：

- 学习期非空且每key恰一次：构建原Gama无缓存候选，调用**同一个**冻结`E5.gama`函数，使用其原评分和tie-breaking，返回原函数选中的结构。
- 有重复：原样委托`ra6.select6`，不改预测/分配/缓存，也不引入zero-tree。

严格same-Gama保证由共同代码路径给出，不再依赖“RA评分和Gama评分自然完全相同”这一未经补足的连接步骤。完整论证的输入域和确定性前提写在报告里。

## 不掩盖原问题

第30轮发现评分口径不同，但限定18设置未找到选择逆序反例；本轮没有把它改写为“反例已证明”。新变体的保证也不能证明原实现对所有输入都等价。

实际运行时比较模型数组、区域边界、BF布局、位图和全pool flags的`uint8`视图、dtype与shape，是真实逐字节比较；hash只用于留档核验。全部预算与全成员BF零FN检查通过。140案例仍来自旧主表，不是140个独立样本；确定性fresh的重复seed不制造独立性。

这是2026-11-22的事后变体，不能说它在MAWI24留出之前已存在。它不保证未来FP最优、不保证不输BF+Cache，也不保证低延迟；RA6-ZGate是另一个付出回放成本的变体。

## 复核

```sh
.condaenv/bin/python -I windows_research/round32_no_repeat_guard/src/test32.py
python3 windows_research/round32_no_repeat_guard/src/report32.py
```

3项单测通过；正式运行拒绝覆盖已有结果。计数、选择/构建、payload核验、尾段评估分别计时；不继承原统计式选择的旧加速倍数。

论文未再改动，结论仅写在本MD与执行计划。

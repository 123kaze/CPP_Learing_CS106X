# 第十二轮：无模型强基线、成本与部署核验

这是投稿前的**实验侧**补充，不修改论文、不修改冻结 RA6、不按新结果调参。

**已完成：14/14 个任务、3064 个基线结果行。** 首先阅读 [`results/结论.md`](results/结论.md)，完整逐项比较见 [`results/report.md`](results/report.md)。不利结果、旧统计勘误和成本边界均保留。

## 目的与状态

- 在 COD、URL、Shalla 的既有设置上比较 RA6 和普通 BF＋缓存，避免只证明“缓存比无缓存有效”。
- 同时核验既有 TCP-only 场景，纯 BF 按实际保留的数组开销收费，而不是沿用模型结构的数组头。
- 90 次原版 Gama / RA6 构建记录的成本拆分和测量边界。
- 指纹缓存的部署状态、固定数据碰撞检查、TCP 特征重合统计的勘误。
- 一个**真正从头执行**的小规模端到端入口：生成数据、训练、选择、构建、原生查询。它只作正确性/可运行性检查，不用作性能证据。

正式方案在 `plan/design-freeze.md`，运行代码与依赖哈希在 `plan/freeze.json`。本地记录不是独立第三方预注册。

## 最小端到端入口（无原始数据依赖）

在仓库根目录，用已经含 NumPy、Numba、LightGBM、SciPy、pandas 的主环境：

```bash
.condaenv/bin/python windows_research/round12_nomodel/src/minimal_e2e.py --output reproduced/e2e.json
```

- 随机种子固定；生成 20,000 行合成数据、5 万次学习查询、15 万次评估查询。
- 训练一个 200 树模型，运行冻结 RA6 / 共享 Gama 及 BF＋缓存。
- 使用紧凑模型数组、真实 BF 位图、真实 CLOCK 缓存逐次查询；核对 LightGBM 分数、成员不被拒绝、全负例池标志和尾流回放计数。
- 不下载数据、不使用预训练缓存、不写入旧轮次的数据目录。
- 会报告含 JIT 的总时间；**不是严肃的性能比较**。当前示例中 BF＋缓存优于 RA6，原样保留，不为让 RA6 获胜而更改生成器。
- 这是带索引部署路径的检查；fp64 的边界另见 `results/deployment_audit.md`。

## 正式无模型对照（需要原先准备好的数据缓存）

```bash
cd windows_research/round12_nomodel
../../.condaenv/bin/python src/test_baseline.py -v
# Mac：串行、保持唤醒、任一任务失败则非零退出
caffeinate -s -i bash src/run_all.sh
../../.condaenv/bin/python src/report12.py
python3 src/verify_results.py          # 只需标准库；核验已提交结果，不需原始数据
python3 src/verify_results.py --inputs # 实验机上另核验数据缓存与来源哈希
```

`src/check_reference.py <url|cod|shalla>` 可单独重跑一个代表性 RA6 案例，并核对新旧数据加载器和存档 FP/树数/缓存；三个数据集均已通过。

单独运行或续跑：

```bash
../../.condaenv/bin/python src/run12.py --dataset url --cache fp64
```

- 750 个合成案例 + 16 个 TCP-only 案例，两种缓存格式，共 1532 个 cache-specific 案例、3064 行 BF/BF＋缓存结果。
- 每个数据集/缓存组合独立 CSV 和输入哈希；断点续跑拒绝混入不同输入、协议或运行代码。
- 实验前检查冻结哈希；不使用旧轮次的输出目录。
- 不自动训练缺失的模型或下载缺失数据：明确失败，避免把准备错误当作新实验。
- 主表与探测重放单列，采用存档参照 FP≥30 筛选，完整未筛选计数仍保存。
- `completion.json` 只有全部预定任务完成才生成；`report12.py` 不接受不完整结果。

## 审计与成本图（不重新计时）

```bash
../../.condaenv/bin/python src/audit_costs.py
../../.condaenv/bin/python src/audit_deployment.py
../../.condaenv/bin/python src/plot_costs.py
```

- `construction_cost.md` / `construction_rows.csv`：总时长、可测阶段与不能拆开的部分。每阶段中位数不作相加。
- `figures/construction_cost.png` / `.pdf`：第八轮 URL 128 KiB、COD 256 KiB 的成本；Matplotlib 直接导出，不使用 LaTeX 编译器。原始表格覆盖全部预算与两种工作负载；`--theme dark` 可生成独立暗色输出。
- `deployment_audit.md` / `.json`：固定成员与测试负例的完整 64 位指纹碰撞检查、真实部署状态与宿主工作区的区别；不声称任意查询严格零假阴性。
- 同一审计还复核旧 `src*2**33+dst` 统计丢失精度的问题：TCP-only 的模型输入重合比例应约为 30%–74%，不是 40%–83%。不改变旧成员划分、训练输入或 FP 测量。

## 阅读边界

Gama、RA6 和 BF＋缓存的比较包含模型、分段分配与选中缓存大小的差异，不等于仅有重新加权的纯消融。没有超过普通 BF＋缓存的场景必须保留。选择加速不意味着完整构建加速；本轮日志时间也不能替代空闲机器上的串行稳态计时实验。

# Stacked 基线：两种实现分别是什么，为什么要自己写 learned stacked（2026-10-31）

论文里出现两个"Stacked"，来源不同，用途也不同，不能混用。

## 1. 原版 Stacked Filter：作者源代码

- **来源**：Stacked Filters（VLDB'21）官方仓库 `bitbucket.org/HarvardDASlab/stackedfilters`，提交 `6e04ca6`。
- **代码**：`original_baselines/stacked/`
  - 驱动 `stacked_orig_driver.cpp` 直接包含原版头文件，用 Bloom 层和 64 位 `BigIntElement`。
  - 为了在 macOS/clang 上编译，用 `overlay/` 覆盖头文件：只把用不到的商过滤器层和 Cuckoo 层换成空桩，并在 `StackedFilter.h` 的副本里改了两处（`std::min<size_t>`，删去这两层的显式实例化），见 `port.patch`。层数、各层大小的优化器和查询逻辑没有改。
  - 运行脚本 `run_stacked_orig.py`：已知负例取学习期（流的前 25%）出现过的 key，按学习期频率降序排列，cdf 为累计查询占比；总位数等于整个预算。
- **结果**（`original_baselines/结论.md` 第 3 节，逐条记录在 `original_baselines/stacked/out/`）：
  - 低预算下只建 1 层，退化成普通 BF；
  - 经常超预算，多数在 1.0–1.34 倍，个别运行达到 4.8–5.2 倍；
  - 即使多用了内存，误报也比 RA-PLBF 多 1–3 个数量级。
  - MAWI 2023 留出集上：16/24/32/128KiB 的误报是 1,495,474 / 179,133 / 78,447 / 3，网格是 47,222 / 12,229 / 3,827 / 0。
- **定位**：原版 Stacked Filter 不使用学习模型，是一个纯过滤器。论文里只能当作"不用学习模型"的背景对照，不是 RA6 的主要对手。写的时候要注明它会超预算，超出的比例逐条可查。

## 2. learned stacked：我们自己的实现

- **为什么没有作者源代码**：learned stacked 指"学习型过滤器后面叠 stacked 侧层"。用 Gama 的模型做底座，后面叠一个负 BF 存学习期误报，再叠一个正 BF 补回被负 BF 误拦的成员。这个组合来自最初任务表的 B1 项（"learned stacked 改为学习期调参"），没有哪篇论文给出过代码，只能由我们实现。
- **实现**：
  - 第二轮：`windows_research/round2_backlog/src/learned_stacked.py`、`run_stacked.py`，旧引擎（100 段分配器、2 的幂桶数缓存）。
  - 第五轮引擎上的版本：`round6_bucket/src/e7_extra.py`（`choose_stacked`、`stacked_layers`）和 `round6_bucket/src/stacked_full.py`（全部 30 个设置、1146 个案例）。
- **选择方式**（沿用第二轮）：
  - 树数用 Gama 选的；
  - 从预算里拿出 frac 建两个侧层，frac × b2 在学习期前半段建层、后半段挑选；
  - 选定后用整个学习期重建；
  - 侧层放不下或者不如不用时，退回 Gama。
- **为什么放进我们的引擎**：记账口径（打包 BF、数组头）、查询流、学习期和评估段都和 RA6 完全相同，比较才公平。每个案例都检查不超预算、零假阴性。
- **结果**：见 `results/stacked_结论.md`。对冷启动的 RA6，按误报总量它在 5/30 个设置上更少；对缓存预热的 RA6-warm，只在 2/30 个设置上更少（cod 256、url 64）。

## 3. 论文里怎么写

- 原版 Stacked Filter：作者代码，无模型基线，注明会超预算。
- learned stacked：把 stacked 的思路接到学习型过滤器上的强基线，**由我们实现**，写明选择方式，代码随论文公开。
- 不能把 learned stacked 写成"Stacked Filter 原文的方法"，也不能把原版 Stacked Filter 的数字当成 learned stacked 的结果。

## 4. 可以加强、但还没做的

审稿人可能质疑"learned stacked 是不是被写弱了"。可以把 learned stacked 的两个侧层换成原版 StackedFilter 库：模型底座仍是 Gama，侧层由作者代码构建，侧层预算由我们限定。难点是原版优化器自己决定层大小，会超预算，需要加一层截断，而截断本身也是一种改动，要单独说明。这一步目前不是必须的。

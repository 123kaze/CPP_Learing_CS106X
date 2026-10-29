# original_baselines：用各论文的官方代码重跑对照方法

流、学习期（前 25%）和评估段（后 75%）与 `windows_research/round3_ra_plbf` 完全相同。结果汇总在 `report.md`，由 `compare.py` 生成；每个基线的原始输出在各子目录的 `out/` 下。

## 仓库与版本

克隆到 `repos/`（不进 git，需要时重新克隆）：

| 基线 | 仓库 | 提交 |
|---|---|---|
| Gama（CIKM'25） | github.com/Spatio-Temporal-Lab/LBF-Gama | 27a454a |
| PLBF（ICLR'21），fast PLBF 实现 | github.com/atsukisato/FastPLBF；另见 github.com/kapilvaidya24/PLBF | 9491e7e；7ed767e |
| Stacked Filter（VLDB'21） | bitbucket.org/HarvardDASlab/stackedfilters | 6e04ca6 |
| AdaptiveQF | github.com/splatlab/adaptiveqf（与 saltsystemslab/adaptiveqf 同一提交） | 6a6ca59 |
| SkiQF / HybridSkiQF（SIGMOD'26） | github.com/saltsystemslab/SkiRentalAdaptiveQF | 28b8b2b |
| TAF（ESA'21，仅克隆备查） | github.com/djslzx/telescoping-filter | 286a936 |

**TODS "To Adapt or to Cache"（CAF）没有公开代码**，对照仍是第二轮按论文描述做的复现（普通 BF＋负例缓存，在学习期调缓存比例）。

## 每个基线怎么跑、改了什么

- **Gama**（`gama/`）
  - `run_gama_plbf_ada.py` 是 `lgb_url_GamaPLBF_ada.py` 的逐行副本。改动都标了 ADAPTER：数据路径、预算列表、预算不可行时记录而不崩溃、输出每个查询 key 的误报标记。搜索逻辑（前 5 轮拟合大小、贝叶斯优化选轮数、FastPLBF_M 50 段 5 区）、模型参数和 pickle 记账都没有改。
  - `export_csv.py` 把我们的划分导出成它的输入格式；`url_sample0.1.csv` 按 `dataset/get_sample.py` 的逻辑生成。
  - 运行环境是 `Bloom/.condaenv_gama`（Python 3.10，bloom-filter 1.3.3，pybloom_live 4.0.0，bayesian-optimization 3.4.0，LightGBM 4.7.0）。
- **PLBF**（`plbf/`）
  - `run_fastplbf.py` 调用仓库原样的 `FastPLBF_M`（N=1000，k=5；与原 PLBF 构建出同一结构）。用验证负例构建，用测试负例池查询。
  - 模型取统一 200 树模型的前缀，分两种：固定 48 树，以及该预算下 Gama 式搜索选出的树数。备份 BF 内存 = 预算 − 模型数组字节数。
- **Stacked**（`stacked/`）
  - `stacked_orig_driver.cpp` 直接包含原版头文件，用 Bloom 层和 64 位 `BigIntElement`。
  - 为了在 macOS/clang 上编译，用 `overlay/` 覆盖头文件：只把用不到的商过滤器层和 Cuckoo 层换成空桩，并在 `StackedFilter.h` 的副本里改了两处（`std::min<size_t>`，删去这两层的显式实例化），见 `port.patch`。编译参数：`-D_GLIBCXX17_INLINE=inline -include cassert`。
  - 负例为学习期见过的 key，按学习期频率降序排列，cdf 为累计查询占比；总位数等于整个预算。原版会超预算，实际位数逐条记录在 `out/`。
- **AdaptiveQF**（`aqf/`）
  - 用官方 C++ 封装 `AdaptiveQF<LocalMap>`。核心源码在 `port/` 里做了 arm64 移植：popcnt、bsr 换成内建函数，rdtsc（只在注释掉的计时代码里用到）、sysinfo、sched_getcpu 换掉，见 `port.patch`。
  - 官方 `tests/test_e2e_localmap` 在移植版上通过。
  - 槽数按官方 `initializeForCapacity`（负载 0.95）取，余数位数取放得进预算的最大值。整条流按顺序回放，每次误报都调用 `adapt`。
- **SkiQF / HybridSkiQF**（`skiqf/`）
  - 变体头文件原样使用；核心 `gqf.c` 等做了同样的 arm64 移植。
  - 论文的 WiredTiger/SplinterDB 反查表换成编码相同的内存表，只用来找回原 key，不影响误报计数。
  - break-even = 2（论文默认实验的取值）。输入是 key 的 64 位哈希（`QF_KEY_IS_HASH`，与论文基准一致）。

## 重跑

```bash
cd original_baselines
# 克隆 repos/ 后：
bash aqf/build.sh; bash skiqf/build.sh      # Stacked 的编译命令见上
../.condaenv/bin/python -u stacked/run_stacked_orig.py --dataset cod     # aqf/、skiqf/ 同理
../.condaenv/bin/python -u gama/export_csv.py cod && \
  GAMA_REPO=$PWD/repos/Spatio-Temporal-Lab__LBF-Gama ../.condaenv_gama/bin/python -u gama/run_gama_plbf_ada.py gama/data/cod 256,1024 gama/out/cod
../.condaenv/bin/python -u compare.py
```

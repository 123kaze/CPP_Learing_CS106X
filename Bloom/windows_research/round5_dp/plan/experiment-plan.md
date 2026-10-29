# 第五轮实验计划（2026-10-29 收到，逐条执行）

按"先修再跑"的顺序。所有结果写进一张长表 CSV（列定义见最后），以后画图、做统计都从这张表出。

## 第 0 步：重跑之前先修三件事

| 编号 | 要修的 | 怎么修 | 怎么验证 |
|---|---|---|---|
| F-A | 分配器 | 所有方法（Gama、网格、RA4、Gama+固定缓存）统一换到 FastPLBF 的动态规划分段；RA4 只是把每段的负例质量 h_i 换成自己的权重 | 无重复负载上 RA4 = Gama 仍逐位一致；Caida 1024KiB 上 Gama 应接近原版 FastPLBF |
| F-B | 缓存档位 | 组数不再限于 2 的幂，改成任意组数（取模或乘法哈希） | 每行输出 cache_alloc_bytes / cache_reserved_bytes，目标 ≥ 95% |
| F-C | 探测重放负载 | 每个结构重放自己的误报 key；改不了就从主表删掉、放附录 | 对所有方法都对称 |

MAWI 2023 已经用过一次。分配器换了以后方法就变了，冻结 RA4+DP 之后要另找一条从没用过的轨迹（比如 MAWI 2024 的某一天），只跑一次。旧的 MAWI 2023 结果保留，作为第一版的验证。

## P0：写结果之前必须有的

- **E1 主表重跑（DP 分配器）**
  - 数据集：COD、URL、Shalla、CAIDA、MAWI 2020/21/22 流数据；预算：主预算加高预算档。
  - 负载：均匀；Zipf，s ∈ {0.8, 1.0, 1.2}，key 池 1 万 / 10 万 / 全部；全新对抗；真实轨迹。种子：合成 5 个，真实 1 个。
  - 方法：FastPLBF（固定 48 树、无缓存）、Gama（复现）、Gama 原版代码（引用 original_baselines）、Gama + 固定 10% 缓存、学习期网格回放、RA4、事后最优。
  - 指标：fp_tail、fpr_tail、RA4/Gama、RA4/网格、RA4/事后最优、树数 t、缓存字节、物理内存分解。
  - 过关：按总量 RA4 不比 Gama 差超过 1%；无重复负载上与 Gama 逐位一致；对网格的中位数比值 ≤ 1.0。
- **E2 与事后最优的差距**
  - 做法：网格的同一候选集在评估段上全部跑一遍，取最少者为事后最优。
  - 指标：fp(方法)/fp(最优)，遗憾值 =(fp−fp_最优)/fp_最优，对 RA4、网格、Gama、Gama+10% 缓存各算一次。
  - 论文：主表加一列，再画一张遗憾值箱线图。
- **E3 预测准确度**
  - 做法：每个设置的全部候选，记录 RA4 的预测误报和实测误报；分段一级用 measure_segments。
  - 指标：每个设置的 Spearman 秩相关、相对误差（中位数、90 分位）、top-1 和 top-3 命中率、分段一级相对误差；noSA、noGT、mix=0.5 三个版本也算一遍。
  - 过关建议：Spearman 中位数 ≥ 0.9，top-3 命中率 ≥ 80%。
- **E4 构建时间分解**
  - 方法：Gama、网格、RA4、FastPLBF；所有数据集取中间档预算。
  - 分解：训练、打分、选择、建结构；单线程，取 5 次中位数，写明硬件。
- **E5 扩展性**
  - 三组变量（每次只变一个）：候选数 ∈ {6×5, 6×10, 12×20, 12×40}；学习期长度 L ∈ {10⁵, 10⁶, 10⁷, 全量}；Zipf key 池 ∈ {10⁴, 10⁵, 10⁶, 10⁷}。
  - 指标：选择耗时、峰值 RSS、学习期状态字节数、选中配置的评估段误报。
  - 论文：双对数坐标曲线图。
- **E6 关键消融（DP 分配器）**
  - 新增 RA-global：用 RA 的预测选缓存大小，但各段 ε 仍按原始 h 分配。
  - 全部消融：noRepeat、noSA、noGT、mix ∈ {0.5, 1}、表格原式、RA-global。
  - 范围与 E1 相同，可只用 3 个种子；指标是对完整 RA4 的中位数、最坏和真实轨迹比值。

## P1：系统实验（只和 learned filter 比）

- **E7 查询延迟和吞吐**
  - 方法：FastPLBF/Gama、Gama+10% 缓存、网格、RA4、learned stacked、SkiQF 式准入。
  - 做法：沿用 end_to_end.py，单线程，排除 JIT 和预热，重复 5 次。
  - 指标：平均耗时（ns）、p50、p99、吞吐，以及模型 / BF / 缓存三部分的耗时分解。
  - 数据：每个数据集取中间档预算，负载用 Zipf 1.0 和真实轨迹。
- **E8 端到端 SQLite**
  - 方法：同 E7，加 NoFilter。
  - 指标：后端访问次数、平均延迟和 p99、总耗时、相对 Gama 的加速。
  - 后端两档：内存版，以及磁盘版或人为加 50µs。
  - 数据：至少 2 条真实轨迹，加 Zipf 1.0。
- **E9 冷启动**
  - 做法：评估段切成 100 个窗口，记录每窗的误报和缓存命中率；方法是 Gama、网格、RA4。
  - 指标：累计误报曲线、命中率曲线、进入稳态（±10%）所需的查询数。

## P2：稳健性和局限

- **E10 敏感性**：学习期比例 ∈ {5, 10, 25, 50}%（固定最后 50% 为评估段）；前缀位数 ∈ {24, 32, 40, 48}；路数 ∈ {1, 2, 4, 8}。方法是 RA4 和 Gama；4 个代表设置。
- **E11 分布漂移**：MAWI 2021 学习 → 2022 评估；合成 Zipf 中途整体更换热点。看 RA4 会不会比 Gama 更差。
- **E12 统计检验**：合成负载报均值和 95% 置信区间；真实轨迹做按窗口的块自助法；整体做 Wilcoxon 符号秩检验（RA4 对网格、RA4 对 Gama）。
- **E13 新的独立验证集**：冻结 RA4+DP 后写预先声明，在新轨迹上只跑一次。

## 统一结果表（每行 = 方法 × 设置 × 种子）

```
dataset, budget_kib, workload, zipf_s, pool, seed, method, allocator,
trees, cache_reserved_bytes, cache_alloc_bytes, model_bytes, bf_bytes, metadata_bytes, overhead_bytes, total_bytes,
fp_tail, fpr_tail, fp_oracle, pred_fp, cache_hit_rate,
t_train_s, t_score_s, t_select_s, t_build_s, learn_state_bytes, peak_rss_bytes,
query_ns_mean, query_ns_p50, query_ns_p99, backend_calls, e2e_ms_mean, e2e_ms_p99,
code_commit, hardware
```

每行断言 total_bytes ≤ budget_kib×1024，且假阴性 = 0。

## 执行顺序

1. 修 F-A、F-B、F-C，用小设置验证：退化是否仍逐位一致，缓存利用率是否 ≥ 95%。
2. E1 + E2 + E3 在同一个循环里跑（计算量最大）。
3. E6。
4. E4、E5。
5. E7、E8、E9。
6. E10、E11、E12。
7. E13，最后、只跑一次。

时间不够时，优先保 E2、E3、E5 和 RA-global 消融。

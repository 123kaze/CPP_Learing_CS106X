# 原审查与输入材料核实

审计日期：2026-10-28。这里只读取原目录，所有脚本和输出写入 `windows_research`。压缩包和粘贴文字是审查材料；其中“改私有仓库”等建议未视为用户授权，不执行远程仓库变更。

## 审计结论

审查提出的缓存内存、学习期网格基线、端到端成本和 TODS 定额问题成立。但“同内存”问题涉及缓存以外的模型、BF 和草图，不能只把缓存条目压到 28 bit 就宣告整个系统在实测预算内。MAWI 2020 已有完整结果和后验处理记录，不能在本次工作中重新宣布为从未接触过的最终留出集。

## 数据来源与压缩包

- 用户附件 `E:/Download/Browser Download/results 2.zip` 与原目录中的 `learned_adaptive_hybrid/results 2.zip` SHA256 相同：`4b0a50142ce5b4dbb81ccc0354f08a8b621bbae49afb73f5d1fd0a4d00a00e44`。
- 压缩包 331 个条目，压缩后 1,924,280B，解压后合计 19,011,370B，包含 macOS 资源叉。没有原始 CSV、NPZ、NPY、PCAP 或训练模型权重。
- 其中 40 个 `rows*.json` 与原目录对应文件的 JSON 内容完全相同；Windows 换行造成字节层面不同。压缩包没有后来增加的 MAWI 结果，MAWI 的审计依据为现有原目录。
- 本地 COD 原始文件在 `LBF-Gama/dataset/raw/cod/{train,test}.csv`。项目中没有 Caida CSV、MAWI CSV 或原项目的评分缓存。原 README 给出 Caida 来源为 `https://github.com/saltsystemslab/How-to-Train-Your-Filter`，代码快照声称固定 `c970c34`，压缩数据应在该上游仓库 `data/compressed/caida.tar.gz`。下载与复现实验由新目录的运行脚本记录。

## 缓存和总内存

| 核实项目 | 原代码证据 | 含义 |
|---|---|---|
| 每条缓存只计前缀+6 bit | `common.py:291–304`，`out[i] = lcp + 1 + LEN_BITS` | 没有计空槽、淘汰状态、查找元数据 |
| 前缀确实避开全体静态成员 | `common.py:183–185`，对排序后的 `h1m` 查前驱与后继 | 完整 64-bit 哈希碰撞时成本置 0，拒绝缓存；静态成员集安全 |
| 原策略仿真按 key 身份命中 | `exp4_cache_policy.py:87` 起，`in_cache[n_pool]` 以及 `prv/nx` | 是理想容量模型，不是紧凑字节实现 |
| 微基准每槽 16B | `bench_cache_overhead.py:build_table`，uint64 hash + int64 length | COD/Caida 都有 16,384 槽，即 262,144B；相对 256KiB 的10%定额 26,214.4B，为10倍 |
| 模型按树数乘700B计 | `common.py:50,430` | 是原生表示估计，不是 LightGBM 对象、文本模型或 NumPy 遍历数组实测 |
| BF 位数组实际一位用一字节 | `common.py:456`，`np.zeros(..., np.uint8)` | 仿真器的 BF 缓冲区为逻辑位负载的8倍；部署版应真打包，并报告段元数据 |
| 草图定额5128B只是假设编码 | `exp9_fp_stream_controller.py:40–42` 与 `exp12_gama_cache.measure` | 原测量 HLL 实际 int64：两份16,384B；Space-Saving三份256项int64共6144B；至少22,528B加计数器，未含流切片等临时内存 |
| 成员检索索引被排除 | `common.py:184`排序成员64-bit哈希 | 若常驻私有排序索引，至少8B/成员；复用后端索引与私有索引应分别报告 |
| 动态成员插入未实现 | 在src未找到新成员更新入口 | 当前证明和实验只适用于固定成员集；新增成员前需失效冲突缓存或重建，不能把文字设想说成已有实现 |

原微基准延迟来自 macOS 的宽哈希表，不能转用于 Windows 紧凑 CLOCK，也不能称为“只花28 bit/条时约7ns”。新的实现和时序必须重新测量。

## Stacked 超预算

全量 `rows_*.json` 共有913个原版 Stacked 运行，其中716个的 `actual_bits / budget_bits > 1`。考虑容差：387个超过1%，373个超过5%，176个超过10%；25个超过2倍，15个超过5倍。完整明细在 `results/audit_existing.json`，按数据集预算汇总在 `results/stacked_budget_audit.csv`。

关键设置：COD 256KiB全部75次为1.14049倍；Caida 128/256KiB各95次为1.06821倍；COD 1MiB最大5.09933倍；Shalla 1MiB最大5.15733倍。原审查对主要数值的判断成立。不能把这些运行放入严格预算内排名；本次采用显式标记实际内存的允许选项，不冒称已经把原版 Stacked 压回预算。

## 学习期和 TODS

- `exp10_baselines.py:182–186` 把 TODS 缓存占比固定为 `n_mem/(budget_bytes*8)`，即每成员1bit；文件开头明确这是作者自己的解读。
- `exp13_deployable.py` 只用前25%查询测量，外推生命周期后选择树数和缓存比例；后75%计分，部署结果的学习窗口口径合理。
- 原有结果没有“同学习期逐树数×逐缓存比例真实回放”的 Gama+LRU 网格调优基线，因此贡献3的效果与成本都需要新增比较。
- 主方法实际草图空间与参数选择成本应分开列：学习器输入存储、候选结构构建、优化计算、部署状态均有不同边界。网格基线也应计保存学习轨迹或并行模拟候选的状态；不能只数一个数组后与完整主方法RSS比较。

## MAWI 独立性

`results/real_traces/结论.md:3` 已说明 MAWI 结果进入实验10–14。该文档说“规则和各方法都没有调参”，但同时记录过检查后修改特征口径：把 tcpdump 净载荷长度转换成 IP 总长，避免 TCP 纯ACK长度0泄漏协议。这是合理修正，同时证明该数据已经被检查。没有可验证的初次运行之前的代码/参数哈希，无法回溯认证其从未影响设计。

因此本次可以报告 MAWI 2020 复现、跨观测点外部验证；不能写“代码冻结后首次打开MAWI做一次最终独立验证”。新日期（原代码已经登记 `mawi2021_flow`）应在冻结源码和协议后首次处理，记录下载哈希、参数、运行次数和最终结果，不依结果改参数。获取不到时必须保留未完成状态，不能用历史表格替代新实验。

## 原目录保护

`evidence/protected-before.json` 为本次首次操作后对原目录只读建立的 SHA256清单，覆盖 `research` 和 `learned_adaptive_hybrid`，共8018个文件、27,383,286,883B。最终执行：

```powershell
python -u windows_research/src/audit_existing.py verify
```

脚本重新哈希并比较文件集合、文件内容及修改时间，输出 `evidence/protected-verification.json`。只有所有差异列表为空，才声明原目录未修改。

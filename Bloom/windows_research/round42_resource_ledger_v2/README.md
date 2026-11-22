# Round42资源账本v2：修正输入ndarray视图漏计（已核验）

[协议](plan/design-freeze.md) · [63行更正后资源/延迟表](results/resources_and_latency_corrected.csv) · [3seed输入特征账本](results/feature_storage.json) · [核验](results/verification.json)

原第42轮`preparation.feature_matrix_bytes`使用`sys.getsizeof(X)`，但NPZ加载后的X是非owning reshape视图；128B只包含视图头，不能称完整特征矩阵字节。

| 字段 | bytes |
| --- | ---: |
| X逻辑payload：39415×20×float32 | 3153200 |
| X视图浅大小（原误命名字段） | 128 |
| 底层owning ndarray：payload＋header | 3153312 |
| 保留视图及base链总和（去重） | 3153440 |

不重复相加logical payload与base物理大小。此链账本仍不是整个训练/harness RSS；key列表、trace、scores、Python/SQLite和其他工作区分别存在。

3项单测通过（owning、reshape view、bytes backing）。冻结后读取旧输入与3worker，核验所有63行旧列逐字符串相同，新增明确的payload和retained-chain字段。**没有重测SQL，没有改变FP、Filter Budget、查询计时、选择配置或回本值。** v1源码/JSON/报告保持原字节，并在入口README显式链接此勘误。

此v2是资源披露修正，不是新的独立工作负载或性能重复测量。无论文修改。

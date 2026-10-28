# windows_research

这是一份与旧研究目录隔离的 Windows 补充实验。入口报告：`REPORT.md`（从原始 JSON 自动生成）。实验协议：`plan/experiment-protocol.md`，关键源文件冻结：`plan/holdout-freeze.json`。

所有新代码、缓存、下载数据、实验结果和日志都在本目录中。`vendor/original_src` 是执行前复制的代码；只在本目录内导入、生成 Python/Numba 缓存。不会执行旧目录里的脚本。

## 重跑

环境：本机 `E:/Conda/python.exe`，numpy/pandas/lightgbm/numba。工作目录为本目录。

```powershell
python src/fetch_data.py
python src/runtime.py --prepare cod
python src/runtime.py --prepare caida
python src/runtime.py --prepare caida_flow
python src/test_caches.py
python src/run_experiments.py --dataset cod --backend clock
python src/run_experiments.py --dataset caida --backend clock
python src/run_experiments.py --dataset caida_flow --backend clock
python src/run_experiments.py --dataset cod --backend global_lru
python src/run_experiments.py --dataset caida --backend global_lru
python src/run_experiments.py --dataset caida_flow --backend global_lru
```

参数 `--queries 10000000 --seeds 5 --workloads all` 可运行更大的历史规模；将覆盖相同输出目录，应先复制本轮结果。默认新实验使用1M×3种子、7种代表负载，不能和历史10M×5种子混为一次重跑。

```powershell
python src/freeze_holdout.py verify
python src/runtime.py --prepare mawi2021_flow
python src/run_experiments.py --dataset mawi2021_flow --backend clock
python src/run_experiments.py --dataset mawi2021_flow --backend global_lru
python src/end_to_end.py --dataset cod --budgets 256,1024 --output-dir results/end_to_end_fixed
python src/end_to_end.py --dataset caida --budgets 128,256 --output-dir results/end_to_end_fixed
python src/summarize_results.py
python src/audit_existing.py verify
```

MAWI holdout 冻结和首次运行已由日志记录，之后重跑只能称复现，不能再次称“首次独立验证”。端到端测量应在机器空闲、没有训练或网格任务时运行。后端延迟是计算投影。

核心限制：实测数组状态预算包含紧凑模型、packed BF、导航/草图及cache开销；权威成员索引另列。COD的索引为24MB，不能把KiB过滤器预算写成整个系统内存。Python解释器/JIT/输入与搜索构建工作集也不包含在KiB声明中。

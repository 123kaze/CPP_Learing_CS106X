# round3_ra_plbf：方法 C（重复感知的分段分配，RA-PLBF）

对应总任务表（`PassCache全部待办.xlsx`）里的 C1–C4，第一阶段的 F1–F4 和 R1 已在第二轮完成。本轮在 Mac 上执行，复用第二轮引擎 `round2_backlog/src/engine.py` 的物理记账、流、学习期和冷启动尾段。在同一批流上，基线（Gama、误报流模型、学习期网格、固定 48 树＋缓存网格）和第二轮 Windows 的结果逐行核对（报告里的"与第二轮一致"列）。

- 算法、与设计表的差异、冻结的常数和开发集：`plan/design-freeze.md`；代码和数据哈希：`plan/freeze.json`。
- 代码：`src/ra_plbf.py`（方法本身），`src/run_c.py`（对比实验），`src/report_c.py`（汇总）。
- 结果：`results/main/<数据集>/<KiB>.json`，汇总在 `results/main/report.md`；开发集结果在 `results/dev/`，不计入正式结论。

## 重跑

数据准备与第二轮相同：先跑 `windows_research/src/runtime.py --prepare {cod,caida,caida_flow,mawi2021_flow}`，再跑 `round2_backlog/src/prepare_datasets.py shalla url caida_flow mawi2021_flow mawi2022_flow`。原始文件的 SHA256 与第二轮记录一致。

```bash
cd windows_research/round3_ra_plbf
../../.condaenv/bin/python -u src/run_c.py --dataset cod --budgets 256,1024
../../.condaenv/bin/python -u src/report_c.py --tag main
```

每个（负载, 种子）完成后都会写检查点，中断后重跑会从断点继续。

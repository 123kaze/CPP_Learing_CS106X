# round4_ra_plbf：RA-PLBF 根因修正、消融与 MAWI 2023 独立验证

- **结论：** `结论.md`。
- **诊断与冻结记录：** `plan/design-freeze.md`（含开发集诊断表）；代码哈希在 `plan/freeze.json`；独立验证的预登记在 `plan/holdout-predeclare.json`，写于下载之前。
- **代码：**
  - `src/ra4.py`：第三轮 `ra_plbf.py` 的副本，只加了开关。第三轮的代码不动。
  - `src/run4.py`：运行各变体。基线复用第三轮在同一批流上的确定性结果。
  - `src/report4.py`：生成汇总报告。
  - `src/holdout.py`：注册 MAWI 2023，再原样运行任意脚本。
  - `src/fetch_holdout2023.py`：解析器，与 MAWI 2022 相同，只改了日期和路径。
- **结果：**
  - `results/main`、`results/high`：常规预算和高预算★点；
  - `results/holdout`：MAWI 2023；
  - `results/diag`：开发集诊断；
  - 汇总：`results/report_main_high.md`、`results/report_holdout.md`。

## 重跑

```bash
cd windows_research/round4_ra_plbf
../../.condaenv/bin/python -u src/run4.py --dataset cod --budgets 256,1024 --tag main
../../.condaenv/bin/python -u src/report4.py --tags main,high
# MAWI 2023：先下载前 120MB 到 data/，然后
../../.condaenv/bin/python -u src/fetch_holdout2023.py parse && ../../.condaenv/bin/python -u src/holdout.py prepare
../../.condaenv/bin/python -u src/holdout.py run src/run4.py --dataset mawi2023_flow --budgets 16,24,32,128 --tag holdout
```

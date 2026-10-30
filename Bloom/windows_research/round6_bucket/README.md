# round6_bucket：方案 D（按实际桶负载精算，RA6）

- **方法与冻结记录：** `plan/design-freeze.md`，冻结时间 2026-10-29 18:00；代码哈希在 `plan/freeze.json`。
- **独立验证集预登记：** `plan/holdout-predeclare.json`，写于下载之前。
- **代码：**
  - `src/ra6.py`：方法；
  - `src/run6.py`：主表，只算 RA6；
  - `src/report6.py`：报告；
  - `src/holdout6.py`、`src/fetch_holdout2024.py`：独立验证集。
- **结果：**
  - `results/report.md`：主报告，不含探测重放，比值只统计参照值不少于 30 次的案例；
  - `results/main/`：主表的行；
  - `results/holdout/`：MAWI 2024，包括第五轮方法在该轨迹上的行 `round5_methods/`，以及结论。

## 基线来自第五轮

RA6 在第五轮完全相同的流上运行。基线（Gama、FastPLBF48、原版 Gama、Gama+10%、网格回放）、RA4 和事后最优都是确定性的，直接取第五轮的行。

第六轮冻结时（2026-10-29 18:00），第五轮的主运行还没有结束：Caida 128/256、Shalla 256/1024/4096、URL 128 等设置是在冻结之后才跑完的。这些行用的都是冻结的第五轮代码。2026-10-30 已逐个核对，`run5.py`、`engine5.py`、`ra5.py`、`dp_alloc.py`、`cache5.py` 的 SHA256 与第五轮、第六轮的冻结记录完全一致。之后只改过计时脚本 `e4_timing.py`，它不参与选择和评估。

## 重跑

```bash
cd windows_research/round6_bucket
../../.condaenv/bin/python -u src/run6.py --dataset cod --budgets 256,1024,4096
../../.condaenv/bin/python src/report6.py
```

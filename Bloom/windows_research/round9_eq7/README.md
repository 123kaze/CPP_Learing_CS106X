# round9_eq7：式 (7) 有限窗口修正的离线诊断

这一轮不改方法，只检验一件事：如果把 RA6 每 key 缺失数的公式（论文式 7）换成带窗口截断的准确形式，预测偏差和配置选择会变多少。冻结的 round4–round6 代码只被导入，没有修改。

- `src/eq7_offline.py`：重建 E3 的同一批候选（合成数据种子 1–4 的前 10，MAWI 2024 的全部候选），分别用原式和修正式按实际桶负载预测。原式的预测要逐个与 E3 存档一致（断言）。
- `src/run_all.sh`：全部任务，4 个并行，约 30 分钟。
- `src/report.py`：生成 `results/report.md`。
- 结论：`results/结论.md`。

```bash
cd windows_research/round9_eq7 && src/run_all.sh && ../../.condaenv/bin/python src/report.py
```

# 第十三轮：基线全覆盖与分块叶子打分

本轮回应两项实验请求，不修改论文或旧冻结代码：

1. 补全 CAIDA 合成、原 4 条 UDP/TCP 真实轨迹、MAWI-24 的普通 BF＋缓存，两种缓存格式均运行。
2. 用分块 `pred_leaf` 一次获取 200 棵树的叶子，按原顺序累加原始分数；验证是否可以透明替换 14 个树数的重复打分，再测成对完整构建时间。

设计见 `plan/design-freeze.md`，两个执行阶段分别由 `baseline-freeze.json` 和 `scoring-freeze.json` 固定代码哈希。MAWI-24 是后续追加对照，绝非新的独立留出集。

## 基线覆盖（已完成）

完整结论见 [`results/基线补全结论.md`](results/基线补全结论.md)，不利案例、低计数结果和 MAWI-24 后续补测性质均保留。

复用第十二轮纯 BF 的实际数组表示、哈希探测、整数 k 选择、13 个缓存比例和学习期回放规则，不改基线定义。

```bash
cd windows_research/round13_complete
caffeinate -s -i bash src/run_baselines.sh
python3 src/report_baselines.py
python3 src/verify_baselines.py          # 无数据缓存的克隆也可核验存档
# python3 src/verify_baselines.py --inputs  # 实验机额外核对原始输入缓存哈希
```

- 新增 400 个案例×两种缓存格式，1600 个 BF/BF＋缓存结果行。
- MAWI-24 另补冻结 RA6-fp64 和 Replay-fp64，共 8 行。
- `results/baseline_report.md` 合并第十二轮和本轮，覆盖原主表 1146、TCP-only 16、MAWI-24 4 个案例，不只列此前的三个合成数据集。
- 原有 UDP/TCP 的任务构造局限仍需披露；补基线不等于消除该问题。

## 打分正确性

```bash
../../.condaenv/bin/python src/test_leaf_scores.py -v
```

检查 14 个树前缀在多种块大小下与 LightGBM raw-score 位相等，以及模型重载、缺失值、空输入等情形。真实 URL 64KiB 的 pilot 也验证了完整分数摘要、once/Zipf 配置、BF 位图与原生 FP 完全一致，并与第八轮存档一致。pilot 不参与正式计时统计。

## 成对完整构建计时（已完成）

最终结论见 [`results/结论.md`](results/结论.md)，全部计时见 [`results/scoring_report.md`](results/scoring_report.md)。60 次构建、30 对等价检查全部通过；20 个组合的配对加速中位为 2.36–2.57×，URL 峰值 RSS 配对中位增加约 8.5%，不宣称普遍节省内存或已快于原版 Gama。

先完成上面的基线任务，避免本项目的两类任务同时占用机器：

```bash
caffeinate -s -i ../../.condaenv/bin/python -u src/run_scoring.py
python3 src/report_scoring.py
python3 src/verify_scoring.py         # 标准库；无原始数据也可核验存档
python3 src/test_verify_scoring.py -v # 10 项存档回归测试
# python3 src/verify_scoring.py --inputs  # 实验机额外核验原始缓存
```

- paper_url / paper_cod × 5 个预算 × 3 次独立成对重建 × loop/leaf，共 60 个进程。
- 每个进程独立训练 200 棵树，两种评分方式的顺序按重复序号交替；全部串行。
- 自动检查模型、14 个分数数组、配置、BF payload、静态池和尾段原生 FP 一致，还核对第八轮存档的配置和计数。
- 一次最多物化 32768×200 的叶子 ID，不创建全数据的巨大叶子矩阵。
- 只声称在测试范围内透明替换；原版 Gama 旧计时仅作历史参考。本轮没有重新计时原版 Gama。
- 若完整构建仍慢于原版或某个设置不加速，保留事实，不预先弱化局限。
- `run_scoring.py` 检查 `baseline_completion.json`，未完成基线时拒绝启动；失败/不完整的既有结果不自动重跑。

## 状态与产物

两部分已完成，核验状态见 `STATUS.md`。基线、pilot 和正式评分使用独立目录；不会覆盖第八、第十二轮记录。需要原先准备好的数据缓存与主 Python 环境，不自动下载数据或安装依赖。

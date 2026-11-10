# 第十四轮：主表八设置的优化后端到端计时

**已完成：72/72个正式进程成功，24/24对RA6等价核验通过。**

[完整英文计时表](results/report.md) · [中文结论](results/结论.md)

不改论文或旧冻结代码。

- 八设置沿用第七轮：四个合成数据集、四条原始真实轨迹及对应预算。
- 同期测量作者原版 G-PLBF、RA6-loop、RA6-leaf；每个设置三个独立重复，共72个正式进程。
- 串行单线程，方法顺序轮换；先运行独立的3进程正确性pilot，通过后自动进入正式实验。
- pred_leaf复用第十三轮冻结helper；14前缀、结构、配置与实际误报均须一致，另外回归第七轮和主表。
- 不预告速度结果，不根据是否胜出挑选设置；不把整个进程时长当构建时间。

```bash
caffeinate -s -i ../../.condaenv/bin/python -u src/run14.py
```

详细协议见 `plan/design-freeze.md`。数据依赖为现有缓存、原版CSV和第七轮固定件，不自动下载或生成。执行日志独立保留在 `results/pilot`、`results/main`；失败后停止，不自动重试。

## 预检路径修正版本

首个版本在训练开始前因错误的输入清单路径停止，0个worker启动。此版本只将清单的缓存路径改为冻结worker实际读取的 round2_backlog/cache；训练、评分、验证和计时协议均不变。失败记录保留在 ../round14_main_e2e/results/。

## 从存档重建表格（不重跑计时）

```bash
python3 src/report14.py --verify-only
python3 src/test_report14.py -v
# 实验机完整核验原始输入与全部上游源文件：
# python3 src/report14.py --verify-only --inputs
```

标准库即可使用；普通克隆没有上游子模块或本地生成的原版适配文件时，会明确报告这些源码未重新核验，不影响从已提交结果重建表格。完整重跑仍需要环境、数据及第三方源码。

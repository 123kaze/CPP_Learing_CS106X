# learned stacked 完整对照的结论（2026-10-31）

数据：`results/stacked_report.md`（由 `src/report_stacked.py` 生成）。learned stacked 用 `src/stacked_full.py`、RA6-warm 用 `src/warm6.py`，都在第五轮引擎上跑完全部 30 个设置、1146 个案例（合成负载 5 个种子），流与主表完全相同。RA6-warm 的冷启动误报在 1146 个案例上都与主表 RA6 逐位相同（逐案例断言）。

## 主要结果

- **和主表的 RA6（缓存冷启动）比，learned stacked 在小 key 池上大幅领先**：逐案例中位数 1 万池 0.008、10 万池 0.082。按误报总量，它在 5/30 个设置上少于 RA6（cod 256、shalla 2048/4096、url 64/128）。
  - 原因是协议不对称：learned stacked 把学习期见过的误报 key 写进常驻的负 BF，评估一开始就生效；RA6 的缓存在评估段从空开始。key 池越小，评估段的误报 key 越多在学习期出现过。
- **RA6-warm（结构不变，缓存先在学习期上回放一遍）把这个优势基本抵消了**：
  - RA6-warm 对 RA6 的逐案例中位数 0.546，主负载上没有一个案例变差；
  - stacked 对 RA6-warm 的逐案例中位数：1 万池 1.000、10 万池 1.000（59% 的案例 stacked 不差）、100 万池 1.42、全部池 1.52、真实轨迹 10.6；
  - 按误报总量，learned stacked 只在 2/30 个设置上少于 RA6-warm：cod 256（0.93）和 **url 64（0.335，约少 3 倍）**。
- **真实轨迹上 learned stacked 很差**：16 个设置里 10 个侧层放不下或不如不用，退回 Gama，误报是 RA6 的 2–55 倍。MAWI 2022 16KiB 上它在学习期后半段选了 frac=0.6，结果比 Gama 还多（988,621 对 403,920）。
- **探测重放下 learned stacked 很差**：对 RA6 的逐案例中位数 8.5，最坏 1.2 万倍，因为负 BF 建好后不再更新。
- **之前 E7 补充里的 Shalla 1024 反例是单个负载的情况**：按全部负载求和，Shalla 1024 上 RA6 427k、RA6-warm 316k、learned stacked 560k。

## 论文里怎么写

1. learned stacked 要作为正式基线列出来，主表同时给 RA6（冷启动）和 RA6-warm。不能只给对 RA6 有利的那一列。
2. 结论只能写成有条件的：同样把学习期知识带进部署时，RA6 在 28/30 个设置上误报更少；小 key 池上两者持平；URL 64 上 learned stacked 明显更好。
3. RA6-warm 只改了部署方式（缓存预热），选择阶段没有考虑预热。所以这不是"RA6 的选择方法优于 learned stacked"，而是"可更新的缓存加上同样的学习期知识，优于静态的负 BF"。
4. learned stacked 的优势场景是"静态、重复的小热点集合"；RA6 的优势场景是真实流量、大 key 池、出现新 key 或重放、小预算。

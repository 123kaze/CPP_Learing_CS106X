# 第55轮：完整无索引主FP矩阵

本轮重新执行原1146case和已见MAWI24四例，不是把第53轮62例复制充数。完整预算/成员FN/原Gama回归通过，完整rawkey cache不依赖成员索引。

| 主1076非probe对照 | 胜/平/负 | 配对平滑比中位 |
| --- | --- | ---: |
| Gama | 837/224/15 | 0.246206 |
| Replay | 414/186/476 | 1.000000 |
| BF+Exact | 1043/2/31 | 0.010351 |
| RA-global | 570/272/234 | 0.996646 |

所有低FP保留，原reference>=30子集与全量并列；probe70例分开。温cache、learned stacked、seed0全加权候选hindsight、seed0–2消融及全seed top10预测均已记录。见results/*.csv和verification.json。

重要：本轮仍复用原模型/分数，因此是完整FP/选择逻辑重跑，不是从训练开始的全部construction或服务延迟重测。后续独立计时/scalability和图形渲染尚未完成；不把本轮完成等同“全文表图已统一”。MAWI24是已用数据的事后exact变体，不是新独立holdout。长key绕过/静态同版本/FN保证前提保留。原prefix结果与论文未改，没有自动发布。

## 并行运行与时间边界

用户授权累计最多5天、每批8小时，并随后允许增加并行度及放宽host内存上限。本轮最多2个独立budget worker，每个native单线程、host RSS最多8GiB、合计16GiB，部署预算仍原KiB值。7pilot显式复用，formal1150case全部新跑。原回放/数值代码未优化。

所有进程内时间属于并行FP批次测量，不能宣传为独占机器选择/构建加速；正式成本表需另做串行重复计时。旧8小时成本gate失败记录完整保留。

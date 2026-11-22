# Round38：预测H误设敏感性

21个固定case keys ×2种cache格式 ×4种预测规则 =168条选择/评估。学习流、真实尾段、预算、模型规则和成员集合固定，只改变两阶段接收的预测H。未截断、复制或延长实际尾段。

33个matched参照复现（旧12例×两格式24行＋ClarkNet-index9行）；ClarkNet-fp64的9个matched配置为新补充，不是留出前证据。

| 格式 | 预测规则 | 案例 | FP较matched胜/平/负 | 平滑FP比中位数 | 最小/最大比 | 配置变化 | payload变化 | top5变化 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| index | quarter | 21 | 12/0/9 | 0.994950 | 0.868750/1.122252 | 10 | 21 | 13 |
| index | matched | 21 | 0/21/0 | 1.000000 | 1.000000/1.000000 | 0 | 0 | 0 |
| index | fourfold | 21 | 10/0/11 | 1.005845 | 0.888589/1.356250 | 11 | 21 | 10 |
| index | three_learning | 21 | 3/12/6 | 1.000000 | 0.964370/1.242744 | 2 | 9 | 1 |
| fp64 | quarter | 21 | 13/0/8 | 0.992283 | 0.753165/1.263158 | 13 | 21 | 13 |
| fp64 | matched | 21 | 0/21/0 | 1.000000 | 1.000000/1.000000 | 0 | 0 | 0 |
| fp64 | fourfold | 21 | 9/0/12 | 1.013110 | 0.827381/1.465116 | 13 | 21 | 10 |
| fp64 | three_learning | 21 | 5/12/4 | 1.000000 | 0.809524/1.058419 | 3 | 9 | 3 |

quarter=floor(H_actual/4)且至少1；fourfold=4×H_actual；matched为正确长度参照；three_learning=3×已观察学习请求数。表中比值先逐case计算(FP_rule+1)/(FP_matched+1)，再聚合，不能说成未经平滑的总FP降幅。

## 全部非matched案例（包括无变化）

| 数据/seed | KiB | 格式 | 规则 | 预测/实际H | matched FP | 实际FP | 平滑比 |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| cod/0 | 1024 | index | quarter | 0.250000 | 45 | 47 | 1.043478 |
| cod/0 | 1024 | index | fourfold | 4.000000 | 45 | 43 | 0.956522 |
| cod/0 | 1024 | index | three_learning | 1.000000 | 45 | 45 | 1.000000 |
| cod/0 | 1024 | fp64 | quarter | 0.250000 | 37 | 47 | 1.263158 |
| cod/0 | 1024 | fp64 | fourfold | 4.000000 | 37 | 44 | 1.184211 |
| cod/0 | 1024 | fp64 | three_learning | 1.000000 | 37 | 37 | 1.000000 |
| url/0 | 128 | index | quarter | 0.250000 | 159 | 138 | 0.868750 |
| url/0 | 128 | index | fourfold | 4.000000 | 159 | 216 | 1.356250 |
| url/0 | 128 | index | three_learning | 1.000000 | 159 | 159 | 1.000000 |
| url/0 | 128 | fp64 | quarter | 0.250000 | 171 | 156 | 0.912791 |
| url/0 | 128 | fp64 | fourfold | 4.000000 | 171 | 251 | 1.465116 |
| url/0 | 128 | fp64 | three_learning | 1.000000 | 171 | 171 | 1.000000 |
| caida/0 | 256 | index | quarter | 0.250000 | 29793 | 30413 | 1.020810 |
| caida/0 | 256 | index | fourfold | 4.000000 | 29793 | 27821 | 0.933812 |
| caida/0 | 256 | index | three_learning | 1.000000 | 29793 | 29793 | 1.000000 |
| caida/0 | 256 | fp64 | quarter | 0.250000 | 30450 | 30215 | 0.992283 |
| caida/0 | 256 | fp64 | fourfold | 4.000000 | 30450 | 30596 | 1.004795 |
| caida/0 | 256 | fp64 | three_learning | 1.000000 | 30450 | 30450 | 1.000000 |
| shalla/0 | 1024 | index | quarter | 0.250000 | 61474 | 61111 | 0.994095 |
| shalla/0 | 1024 | index | fourfold | 4.000000 | 61474 | 54625 | 0.888589 |
| shalla/0 | 1024 | index | three_learning | 1.000000 | 61474 | 61474 | 1.000000 |
| shalla/0 | 1024 | fp64 | quarter | 0.250000 | 77507 | 77812 | 1.003935 |
| shalla/0 | 1024 | fp64 | fourfold | 4.000000 | 77507 | 66658 | 0.860027 |
| shalla/0 | 1024 | fp64 | three_learning | 1.000000 | 77507 | 77507 | 1.000000 |
| caida_flow/0 | 24 | index | quarter | 0.250000 | 376911 | 385969 | 1.024032 |
| caida_flow/0 | 24 | index | fourfold | 4.000000 | 376911 | 380314 | 1.009029 |
| caida_flow/0 | 24 | index | three_learning | 1.000000 | 376911 | 376911 | 1.000000 |
| caida_flow/0 | 24 | fp64 | quarter | 0.250000 | 440292 | 430770 | 0.978373 |
| caida_flow/0 | 24 | fp64 | fourfold | 4.000000 | 440292 | 437893 | 0.994551 |
| caida_flow/0 | 24 | fp64 | three_learning | 1.000000 | 440292 | 440292 | 1.000000 |
| mawi2020_flow/0 | 24 | index | quarter | 0.250000 | 17410 | 17611 | 1.011544 |
| mawi2020_flow/0 | 24 | index | fourfold | 4.000000 | 17410 | 15838 | 0.909712 |
| mawi2020_flow/0 | 24 | index | three_learning | 1.000000 | 17410 | 17410 | 1.000000 |
| mawi2020_flow/0 | 24 | fp64 | quarter | 0.250000 | 17854 | 18673 | 1.045870 |
| mawi2020_flow/0 | 24 | fp64 | fourfold | 4.000000 | 17854 | 19124 | 1.071129 |
| mawi2020_flow/0 | 24 | fp64 | three_learning | 1.000000 | 17854 | 17854 | 1.000000 |
| mawi2021_flow/0 | 24 | index | quarter | 0.250000 | 10347 | 10234 | 0.989080 |
| mawi2021_flow/0 | 24 | index | fourfold | 4.000000 | 10347 | 10285 | 0.994009 |
| mawi2021_flow/0 | 24 | index | three_learning | 0.999999 | 10347 | 10347 | 1.000000 |
| mawi2021_flow/0 | 24 | fp64 | quarter | 0.250000 | 11907 | 10982 | 0.922321 |
| mawi2021_flow/0 | 24 | fp64 | fourfold | 4.000000 | 11907 | 10957 | 0.920222 |
| mawi2021_flow/0 | 24 | fp64 | three_learning | 0.999999 | 11907 | 11907 | 1.000000 |
| mawi2022_flow/0 | 24 | index | quarter | 0.250000 | 19010 | 18874 | 0.992846 |
| mawi2022_flow/0 | 24 | index | fourfold | 4.000000 | 19010 | 19886 | 1.046079 |
| mawi2022_flow/0 | 24 | index | three_learning | 1.000000 | 19010 | 19010 | 1.000000 |
| mawi2022_flow/0 | 24 | fp64 | quarter | 0.250000 | 19904 | 20699 | 1.039940 |
| mawi2022_flow/0 | 24 | fp64 | fourfold | 4.000000 | 19904 | 21180 | 1.064104 |
| mawi2022_flow/0 | 24 | fp64 | three_learning | 1.000000 | 19904 | 19904 | 1.000000 |
| caida_tcp_flow/0 | 32 | index | quarter | 0.249999 | 55050 | 54772 | 0.994950 |
| caida_tcp_flow/0 | 32 | index | fourfold | 4.000000 | 55050 | 54922 | 0.997675 |
| caida_tcp_flow/0 | 32 | index | three_learning | 0.999998 | 55050 | 55050 | 1.000000 |
| caida_tcp_flow/0 | 32 | fp64 | quarter | 0.249999 | 57427 | 57350 | 0.998659 |
| caida_tcp_flow/0 | 32 | fp64 | fourfold | 4.000000 | 57427 | 58283 | 1.014906 |
| caida_tcp_flow/0 | 32 | fp64 | three_learning | 0.999998 | 57427 | 57427 | 1.000000 |
| mawi2020_tcp_flow/0 | 64 | index | quarter | 0.249999 | 68394 | 68795 | 1.005863 |
| mawi2020_tcp_flow/0 | 64 | index | fourfold | 4.000000 | 68394 | 68025 | 0.994605 |
| mawi2020_tcp_flow/0 | 64 | index | three_learning | 0.999993 | 68394 | 68394 | 1.000000 |
| mawi2020_tcp_flow/0 | 64 | fp64 | quarter | 0.249999 | 67627 | 68896 | 1.018764 |
| mawi2020_tcp_flow/0 | 64 | fp64 | fourfold | 4.000000 | 67627 | 69099 | 1.021766 |
| mawi2020_tcp_flow/0 | 64 | fp64 | three_learning | 0.999993 | 67627 | 67627 | 1.000000 |
| mawi2021_tcp_flow/0 | 41 | index | quarter | 0.250000 | 41727 | 41845 | 1.002828 |
| mawi2021_tcp_flow/0 | 41 | index | fourfold | 4.000000 | 41727 | 41487 | 0.994248 |
| mawi2021_tcp_flow/0 | 41 | index | three_learning | 1.000000 | 41727 | 41727 | 1.000000 |
| mawi2021_tcp_flow/0 | 41 | fp64 | quarter | 0.250000 | 42211 | 42861 | 1.015398 |
| mawi2021_tcp_flow/0 | 41 | fp64 | fourfold | 4.000000 | 42211 | 43187 | 1.023121 |
| mawi2021_tcp_flow/0 | 41 | fp64 | three_learning | 1.000000 | 42211 | 42211 | 1.000000 |
| mawi2022_tcp_flow/0 | 64 | index | quarter | 0.249998 | 58339 | 58509 | 1.002914 |
| mawi2022_tcp_flow/0 | 64 | index | fourfold | 4.000000 | 58339 | 58680 | 1.005845 |
| mawi2022_tcp_flow/0 | 64 | index | three_learning | 0.999997 | 58339 | 58339 | 1.000000 |
| mawi2022_tcp_flow/0 | 64 | fp64 | quarter | 0.249998 | 60362 | 59881 | 0.992032 |
| mawi2022_tcp_flow/0 | 64 | fp64 | fourfold | 4.000000 | 60362 | 60155 | 0.996571 |
| mawi2022_tcp_flow/0 | 64 | fp64 | three_learning | 0.999997 | 60362 | 60362 | 1.000000 |
| clarknet/3601 | 8 | index | quarter | 0.249980 | 4491 | 4408 | 0.981523 |
| clarknet/3601 | 8 | index | fourfold | 4.000000 | 4491 | 4538 | 1.010463 |
| clarknet/3601 | 8 | index | three_learning | 0.961967 | 4491 | 4592 | 1.022484 |
| clarknet/3601 | 16 | index | quarter | 0.249980 | 1136 | 1275 | 1.122252 |
| clarknet/3601 | 16 | index | fourfold | 4.000000 | 1136 | 1507 | 1.326297 |
| clarknet/3601 | 16 | index | three_learning | 0.961967 | 1136 | 1412 | 1.242744 |
| clarknet/3601 | 32 | index | quarter | 0.249980 | 137 | 131 | 0.956522 |
| clarknet/3601 | 32 | index | fourfold | 4.000000 | 137 | 155 | 1.130435 |
| clarknet/3601 | 32 | index | three_learning | 0.961967 | 137 | 139 | 1.014493 |
| clarknet/3601 | 8 | fp64 | quarter | 0.249980 | 5150 | 5102 | 0.990681 |
| clarknet/3601 | 8 | fp64 | fourfold | 4.000000 | 5150 | 4995 | 0.969909 |
| clarknet/3601 | 8 | fp64 | three_learning | 0.961967 | 5150 | 5054 | 0.981363 |
| clarknet/3601 | 16 | fp64 | quarter | 0.249980 | 1493 | 1332 | 0.892236 |
| clarknet/3601 | 16 | fp64 | fourfold | 4.000000 | 1493 | 1473 | 0.986613 |
| clarknet/3601 | 16 | fp64 | three_learning | 0.961967 | 1493 | 1511 | 1.012048 |
| clarknet/3601 | 32 | fp64 | quarter | 0.249980 | 146 | 130 | 0.891156 |
| clarknet/3601 | 32 | fp64 | fourfold | 4.000000 | 146 | 140 | 0.959184 |
| clarknet/3601 | 32 | fp64 | three_learning | 0.961967 | 146 | 153 | 1.047619 |
| clarknet/3602 | 8 | index | quarter | 0.249994 | 4237 | 4210 | 0.993629 |
| clarknet/3602 | 8 | index | fourfold | 4.000000 | 4237 | 4297 | 1.014158 |
| clarknet/3602 | 8 | index | three_learning | 0.960540 | 4237 | 4086 | 0.964370 |
| clarknet/3602 | 16 | index | quarter | 0.249994 | 1326 | 1210 | 0.912585 |
| clarknet/3602 | 16 | index | fourfold | 4.000000 | 1326 | 1422 | 1.072344 |
| clarknet/3602 | 16 | index | three_learning | 0.960540 | 1326 | 1379 | 1.039940 |
| clarknet/3602 | 32 | index | quarter | 0.249994 | 142 | 130 | 0.916084 |
| clarknet/3602 | 32 | index | fourfold | 4.000000 | 142 | 134 | 0.944056 |
| clarknet/3602 | 32 | index | three_learning | 0.960540 | 142 | 141 | 0.993007 |
| clarknet/3602 | 8 | fp64 | quarter | 0.249994 | 4435 | 4542 | 1.024121 |
| clarknet/3602 | 8 | fp64 | fourfold | 4.000000 | 4435 | 4920 | 1.109333 |
| clarknet/3602 | 8 | fp64 | three_learning | 0.960540 | 4435 | 4384 | 0.988503 |
| clarknet/3602 | 16 | fp64 | quarter | 0.249994 | 1454 | 1482 | 1.019244 |
| clarknet/3602 | 16 | fp64 | fourfold | 4.000000 | 1454 | 1794 | 1.233677 |
| clarknet/3602 | 16 | fp64 | three_learning | 0.960540 | 1454 | 1539 | 1.058419 |
| clarknet/3602 | 32 | fp64 | quarter | 0.249994 | 167 | 138 | 0.827381 |
| clarknet/3602 | 32 | fp64 | fourfold | 4.000000 | 167 | 138 | 0.827381 |
| clarknet/3602 | 32 | fp64 | three_learning | 0.960540 | 167 | 135 | 0.809524 |
| clarknet/3603 | 8 | index | quarter | 0.249988 | 4277 | 4272 | 0.998831 |
| clarknet/3603 | 8 | index | fourfold | 4.000000 | 4277 | 4248 | 0.993221 |
| clarknet/3603 | 8 | index | three_learning | 0.926343 | 4277 | 4261 | 0.996260 |
| clarknet/3603 | 16 | index | quarter | 0.249988 | 1221 | 1108 | 0.907529 |
| clarknet/3603 | 16 | index | fourfold | 4.000000 | 1221 | 1359 | 1.112930 |
| clarknet/3603 | 16 | index | three_learning | 0.926343 | 1221 | 1272 | 1.041735 |
| clarknet/3603 | 32 | index | quarter | 0.249988 | 123 | 132 | 1.072581 |
| clarknet/3603 | 32 | index | fourfold | 4.000000 | 123 | 133 | 1.080645 |
| clarknet/3603 | 32 | index | three_learning | 0.926343 | 123 | 130 | 1.056452 |
| clarknet/3603 | 8 | fp64 | quarter | 0.249988 | 4652 | 4617 | 0.992478 |
| clarknet/3603 | 8 | fp64 | fourfold | 4.000000 | 4652 | 4713 | 1.013110 |
| clarknet/3603 | 8 | fp64 | three_learning | 0.926343 | 4652 | 4787 | 1.029014 |
| clarknet/3603 | 16 | fp64 | quarter | 0.249988 | 1328 | 1187 | 0.893905 |
| clarknet/3603 | 16 | fp64 | fourfold | 4.000000 | 1328 | 1584 | 1.192626 |
| clarknet/3603 | 16 | fp64 | three_learning | 0.926343 | 1328 | 1307 | 0.984199 |
| clarknet/3603 | 32 | fp64 | quarter | 0.249988 | 157 | 118 | 0.753165 |
| clarknet/3603 | 32 | fp64 | fourfold | 4.000000 | 157 | 133 | 0.848101 |
| clarknet/3603 | 32 | fp64 | three_learning | 0.926343 | 157 | 127 | 0.810127 |

## 解释与边界

- 所有选择调用的API均不接受tail数组；H观察器逐次核对stage1和每个stage2调用的H一致，不重算候选表、不改返回对象/排序。
- 相同整数H的重复规则须真实逐字节匹配模型、分区、位图、flags和最终cache；与matched相同payload的案例也须FP与cache状态一致。配置不变并不自动意味着位图不变。
- 全部实体BF构建的有限成员检查0FN、预算通过。最终cache成员命中总数为0；index要求为0，fp64仅记录有限集合观测，仍有理想非对抗hash假设下的单query界，不是普适或生命周期零FN。
- fp64 worker不构建或持有排序成员索引，不计算safe prefix；构建/验证所需成员hash数组仍在harness中。index的8*n+header额外资源单列，不能说成通用后端免费提供。
- 四规则按case循环移位运行，加载、模型/评分、索引、GT摘要、JIT、选择/构建、候选记录、payload复建和评估/成员检查分别计时。单次wall计时和共享日志的seed不是独立时延重复。
- 原论文数据、原真实流、TCP-only、HTTP四类汇总均保留在summary.json，不更换统计分组追求显著性。H误设偶然比matched好不能用来事后选H。
- H可作为计划性复核/重建前的预计negative请求数；3L为只依赖已观察数据的预设启发式，不承诺最优。本轮不是开放流重建/漂移适应实验，也不证明无限期运行保证。
- ClarkNet沿用回溯稳定子集与1995年日志；不新增现代/前瞻部署证据。没有使用MAWI24重新选H，也未改变旧留出记录。
- 旧E10学习比例敏感性与本轮不同：它总是给出实际尾段长度，本轮隔离预测输入误设。代码和结果另轮归档，论文未改。

# Round50：已知完整SIS文件的开发诊断

这是第48/49轮之后的新探索，不是独立holdout，不倒填旧prefix资格。全文件只代表其实际2018-05-23至31日范围；observed HTTPsuccess/404不能证明业务record存在性。

| seed | member train | negative train/val | learning/tail negatives | AUC16 | 1000分段中的member/valnegative占用数 | tail未见key请求比例 |
| --- | ---: | --- | --- | ---: | --- | ---: |
| 5001 | 1374355 | 116/143 | 44919/17274 | 0.45174782800764557 | 40/11 | 0.21813129558874608 |
| 5002 | 1373460 | 103/131 | 2819/5799 | 0.42038282886857514 | 42/6 | 0.6497672012415934 |
| 5003 | 1373807 | 98/103 | 45235/17753 | 0.3273320104891991 | 47/5 | 0.21224581760829156 |

规模/split资格：True；原因：[]。

AUC和16tree score分辨率分开看。极不平衡训练可能导致sigmoid分数集中；本轮不翻转score、不改classweights/样本比例。16tree诊断不能代表整个200tree候选网格已退化或已经成功。便宜path支持规则、重叠、region重复差和完整分项时间在JSON/CSV。

只保留negative流及其原GETordinal，完整source行数/GET数/SHA与第49轮匹配；没有人为增加negative或重排时间。未来严格精确negativecache中member查询不会命中或插入，不改变CLOCK状态；这解释FP诊断可用negative-only流，但它不是完整query延迟计时，也不意味着可以把positive比例隐藏。

原rawkey blob、输入X/ids/工作SQLite都是offline输入/准备工作区，不算免费的部署Filter。没有建立prefix验证memberhash索引；若后续用Exact128必须完整计费并保持static版本保证。

本轮未构造选择五方法、更未测后端服务时间，因此没有RA胜出结论。开发诊断完成后，任何新比较须另冻协议；原source/计数/失败不覆盖，论文未动，未push。

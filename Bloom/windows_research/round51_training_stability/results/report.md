# Round51：训练稳定性开发消融

新训练配方探索，原结果不变。只看开发AUC和数值稳定性，未测实体FP；预选候选固定balanced_clip，不从四个配方事后挑最高AUC。

| recipe | AUC中位 | member bin999比例中位 | member占用segment数中位 | rawscore范围（所有seed） |
| --- | ---: | ---: | ---: | --- |
| original | 0.420383 | 0.998544 | 42 | -5090.726508 .. 199643.388353 |
| balanced | 0.963096 | 0.000000 | 98 | -2.220657 .. 2.937028 |
| clip_only | 0.976347 | 1.000000 | 1 | 7.779905 .. 11.148129 |
| balanced_clip | 0.979355 | 0.000000 | 48 | -1.600000 .. 1.600000 |

进入后续实体方法比较的开发闸门：True。

Balanced使用每类相等总权重、平均样本weight1，不移除或复制训练keys。Clip使用max_delta_step1及lr.1，rawscore相对实际weighted prior的累计变化界核验通过。没有翻转score/标签，没有用tail FP挑配方，没有改stream、预算或旧Frozen算法。

后续若执行，必须同时给Gama/Replay/RA-global/RA相同新配方，原配方作为完整控制，BF不付不需要的模型成本；平衡权重属于新的训练variant，不能改名旧RA6/Gama已获得相同保证或旧holdout。

开发AUC改善不等于端到端或BF+Cache胜出。真实文件整体负请求比例低、热点和冷新key不同、训练过程有成本，都仍需完整对照。当前SIS source已做过探索性inventory/diagnostic，不是独立真实holdout。论文未动，未push。

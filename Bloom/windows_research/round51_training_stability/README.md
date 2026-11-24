# Round51：不平衡训练稳定性消融（开发诊断完成）

[事前协议](plan/design-freeze.md) · [12模型结果](results/rows.csv) · [报告](results/report.md) · [核验](results/verification.json)

原SIS训练约137万positive keys对98–116negative keys，原16tree rawscore出现巨大幅度、member几乎全部落在bin999。此轮研究训练配方，不翻转score或标签，不改请求流，不看实体filter的tailFP。

| 配方 | 开发AUC中位 | member在bin999比例中位 |
| --- | ---: | ---: |
| original | 0.420383 | 0.998544 |
| balanced | 0.963096 | 0 |
| clip_only | 0.976347 | 1 |
| balanced_clip | 0.979355 | 0 |

Original3/3复现第50轮AUC。预先唯一的后续候选是balanced_clip，不从四者中事后择优；三个seed都通过AUC>=.70且相对original增加>=.03的开发门限，clipraw界及有限值核验通过，3项fixture测试通过。

Balanced每类总weight相等、平均weight1，不复制/丢弃key；clip max_delta_step1配合lr.1限制每轮leaf增量。只做clip能改善排序，但所有member仍落入同一个1000分段bin，说明高AUC并不等于原PLBF量化可直接利用。

**这不是RA的独占收益，也不是实体FP或部署胜出。** 若继续，Gama/Replay/RA-global/RA必须共享同一新配方，原配方并列保留；BF无需付模型成本。后续[Round52](../round52_sis_filter_controls/plan/design-freeze.md)按此要求冻结完整对照。

本轮明确是已见SIS文件上的开发探索，不是独立holdout，不追认给旧RA6/Gama/MAWI结果。原第48轮失败资格及第50轮负诊断保持。论文未动，未push。

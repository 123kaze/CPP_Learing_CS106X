# Round52：SIS实体filter结果，原/稳定训练配方并列

完整126主比较/54固定配置控制；不是独立holdout，不是端到端部署计时。真实线上文件来自SIS，但任务是observed-success/404的回溯稳定子集，不能推出业务record存在性。

## 完整主比较

| recipe | RA vs BF 胜/平/负 | 平滑比中位 | RA vs Replay 胜/平/负 | 平滑比中位 |
| --- | --- | ---: | --- | ---: |
| original | 8/0/1 | 0.692683 | 5/0/4 | 0.982699 |
| balanced_clip | 9/0/0 | 0.055210 | 7/0/2 | 0.882353 |

## 每预算三seed的FP中位数（不是配对比）

| recipe | KiB | Gama | Replay | RA-global | RA | BF+Exact | PlainBF | ZGate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| original | 672 | 2290 | 1063 | 1063 | 1054 | 1448 | 2924 | 1054 |
| original | 1343 | 486 | 288 | 313 | 281 | 464 | 981 | 281 |
| original | 2685 | 98 | 45 | 37 | 41 | 58 | 97 | 41 |
| balanced_clip | 672 | 438 | 72 | 79 | 79 | 1448 | 2924 | 79 |
| balanced_clip | 1343 | 67 | 33 | 37 | 29 | 464 | 981 | 29 |
| balanced_clip | 2685 | 25 | 3 | 3 | 2 | 58 | 97 | 2 |

## 必须保留的限制

- balanced_clip是开发段选择的显式新训练配方，同时给所有learned基线，原配方完整保留；BF两配方的结构/FP/最终cache完全一致。不是只给RA更强模型。
- 每配方按实际训练树数报告可行网格；无法训练的prefix不补树、不伪造结果。已有原RA6/GT19/MAWIholdout不被改写。
- 完整input/训练/score/tree/GT/JIT/选择/回放/成员检查分开计时；回放用预计算flags，不是模型/特征/SQL服务时间。
- Exact128严格完整key相等、长key绕过；额外memberhash验证索引0。RA原预测未建模长keybypass，局限保留。
- negative train/val key排除改变各seed评估请求量，尤其seed5002移除了主要热点；所有seed都保留，不能将行数当独立工作负载。
- 全文件HTTP负请求比例很低，负流FP改善不自动覆盖全量query推理、训练、标签或重配置成本。
- 固定h/traffic/miss控制与完整RA配置选择不同；AMGM只对应其正支持/未截断/固定T条件，actual CLOCK的T不是外生。
- ZGate仅保证learning finalist比较，额外回放与两类搜索计费，不保证未来不退化。
- 前200万行失败资格保持，完整文件属于后来明确标注的探索；六月/其他来源还不是已执行独立确认性验证。
- 不改论文、不自动push，所有负方向与可能的失败保留。

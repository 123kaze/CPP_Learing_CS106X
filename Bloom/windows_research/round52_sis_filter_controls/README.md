# Round52：SIS真实线上来源上的实体filter正反结果（已完成并复核）

[冻结协议](plan/design-freeze.md) · [全部126主行](results/main.csv) · [54行固定配置控制](results/controls.csv) · [报告](results/report.md) · [独立复核含最坏例/总FP](../../docs/round52_evidence_20261124/verification.json)

**得到真实来源数据上的FP正结果：新训练配方下RA对同预算BF+Exact128为9胜0负；但尚未证明端到端或生产系统“必须部署RA”。** 完整matrix和原配方控制均保留，不只报告胜出的版本。

## 输入与实验身份

来源是Charles University真实线上SIS access log，2018-05-23至31日、2749058个稳定observed-success target与3467个稳定404 target，原请求顺序保留。它是全文件回溯稳定HTTP响应子集，不代表真实业务record存在性，也不是完整日历月或原生产系统部署实测。

第48轮初始200万行资格失败仍然失败；第49/50/51轮是明确的后续全文件探索/训练诊断。这里的实体FP是首次按已冻结矩阵测量，但数据已经被探索，**不是新独立holdout**。

recipes=original/balanced_clip；3seed×672/1343/2685KiB，每recipe内Gama/Replay/RA-global/RA共享同一训练模型与特征；BF无需付模型训练成本。这里Gama是项目的共享物理计费引擎版本，不是声称重新运行作者官方完整部署系统。

13项preflight检查（3selector、7exact-cache、3training）通过。固定pilot只看资源/时间，非计时结果在正式矩阵复现。6个正式worker顺序完成；全轮433.84秒，正式worker合计379.51秒。全部实际训练到200trees，所有14个原prefix均可用；没有补树或事后删prefix。

## 主要对照

| recipe | RA vs BF 胜/平/负 | 配对平滑比中位 | RA vs Replay 胜/平/负 | 配对平滑比中位 |
| --- | --- | ---: | --- | ---: |
| original | 8/0/1 | 0.692683 | 5/0/4 | 0.982699 |
| balanced_clip | 9/0/0 | 0.055210 | 7/0/2 | 0.882353 |

比值逐case计算`(FP_RA+1)/(FP_baseline+1)`再取中位，不是总FP下降百分比。原配方即有8/9对BF胜出，不能将所有收益只归因于后续训练修复；新配方也同时帮助其他learned方法。

### 新配方全部9个case，保留退化与低FP点

| seed | KiB | Gama | Replay | RA-global | RA | BF+Exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 5001 | 672 | 75 | 72 | 61 | 49 | 1113 |
| 5001 | 1343 | 28 | 22 | 25 | 20 | 464 |
| 5001 | 2685 | 3 | 3 | 0 | 2 | 56 |
| 5002 | 672 | 438 | 365 | 377 | 349 | 1460 |
| 5002 | 1343 | 67 | 53 | 37 | 312 | 713 |
| 5002 | 2685 | 25 | 25 | 3 | 5 | 70 |
| 5003 | 672 | 542 | 71 | 79 | 79 | 1448 |
| 5003 | 1343 | 12160 | 33 | 47 | 29 | 409 |
| 5003 | 2685 | 264 | 3 | 3 | 1 | 58 |

**不能把7/9胜Replay写成整体总FP更低。** 新配方seed5002/1343KiB是明显退化：RA312 vsReplay53（加1比5.7963）。把9配置FP简单相加，RA846、Replay647、RA-global632、BF5791。这个总和不是一条实际部署流（跨预算、相关seed），但必须保留为另一种汇总视角，说明中位胜出/胜率不能隐藏大幅退化。

原配方也有重要负例：seed5001/2685KiB，RA308、Replay45、BF56。原配方9配置合计RA4207、Replay4746、BF5791，原始数字同样留档。

## 选择效率与权重机制

含GT统计的选择阶段对Replay：

- original：9/9更快，配对加速中位3.797×。
- balanced_clip：9/9更快，配对加速中位3.858×，范围2.864–5.662×。

这是候选构建/选择，不含训练、全prefix评分和查询服务。不是整个SIS系统加速3.86×。这些大成员集上Replay需建很多实体BF，不能将结果仅归因为学习流长度或继承旧49×。

固定anchor树/分区/BFbits/10%cache/hashes后，仅改变h/traffic/miss：

| recipe | miss vs h | miss vs traffic |
| --- | --- | --- |
| original | 6胜3负；平滑比中位0.948718 | 7胜2负；0.836364 |
| balanced_clip | 6胜1平2负；0.938462 | 7胜2负；0.500000 |

平滑比0.5不等于未经平滑的整个trace总FP降低50%。新配方仍有控制退化，如seed5002/672KiB的miss391 vs traffic107；中预算miss57 vs traffic43。所有18个连续双内点条件等式核验通过，但actualCLOCK的T不是外生固定，不能把实体7/9改善说成普遍理论最优保证。

## 训练修复与缓存契约

第51轮原训练极不平衡（约137万positive对约100negative）出现巨大rawscore。balanced_clip用两类相等总weight、平均weight1及max_delta_step1；只在开发段按事前门槛选定，不用实体FP挑配方，不翻转score/标签。该配方给全部learned基线；两recipe的BF和PlainBF配置/FP/flags/最终cache字节全部一致。

这是显式新训练variant，**不能改名旧冻结RA6/Gama已获得这些结果，也不替换原MAWIholdout**。原配方RA实际9例均选1tree，而新配方选32/48/64trees，未来真实query成本可能更高，不能由FP结果直接宣称部署更快。

Exact128完整rawtarget byte equality，长key绕过，不依赖成员hash验证索引。全部Filter实占含model/BF/routing/header/cache，额外索引0；126主行和54控制全部预算、静态memberBF及最终membercache0FN检查通过。该保证限静态同版本目录、真实absence反馈；动态成员需失效协议。

各seed约868–889个query-negative keys超过128bytes，tail约996–1005次长key请求不能缓存。原RA预测未单独建模这个bypass，限制如实保留。大rawkey blob、X、score arrays、训练weights是offline输入/准备工作区，不是部署Filter Budget，也不是免费进程内存。

## 必须保留的部署/统计限制

- 原全文件negative请求约0.16%，真实混合查询中的positive占绝大多数；模型32–64tree推理/特征成本尚未实测。本轮不含SQL、远程访问、训练标签采集或重配置总成本。
- Key-heldout split在seed5002移除了主要热点，只保留13.598%原negative请求，另外两seed保留98.132%/99.386%。未删该seed，每方法仍在同seed同流比较，但这不是三份独立实际流量。
- 所有ZGate都在learning选RA，与RA tail相同；这不提供未来不退化保证，额外搜索/回放成本已经记录。
- 回溯目录/冲突排除使用整份文件，source曾被探索；独立时间段/独立应用与端到端部署收益尚未验证。不能把“找到一个真实来源FP正例”改写成“真实系统普遍需要RA”。
- 原数据、私有URL参数、离线cache/DB和工具binary不发布。论文未动，本批未push。

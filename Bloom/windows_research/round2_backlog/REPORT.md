# PassCache 第二轮：非 C 实验结果

源任务为用户提供的 `PassCache全部待办.xlsx` 总任务表，本轮执行完26项非C实验，其中最终留出的Stacked16KiB有1个建层失败点，保留并排除其效果比较；C1–C5及理论、论文写作、仓库权限、联系他人等非实验任务未纳入。实验均保存在本目录。结论是：**缓存有效，但当前误报流模型选配置的精度经常不如学习期网格，现有证据不足以声称它达到网格效果。** 这不是新增C方法的验证，也不是可投稿性或整体净收益结论。

## 1. 完成范围与数据

核验计数：{"primary_rows": 5685, "stacked_rows": 948, "stacked_failed_cases": 1, "native_aqf_rows": 342, "ablation_rows": 1152, "hash_sensitivity_rows": 150, "live_rows": 80, "real_backend_rows": 12, "dynamic_insertions": 1000, "periodic_recalibration_rows": 10}。

重复型负载恢复10,000,000查询、5个配对种子；每key一次和50,000全新高分负例保留其原始长度。模型、划分固定；学习前25%，评估尾75%冷缓存。真实轨迹不伪造5次独立重复。地址特征流程覆盖Caida、MAWI2021、首次冻结后评价的MAWI2022；旧五特征MAWI仅用于F4历史审计。

完整URL原表651,191行、去重641,119个URL。6个URL出现善恶冲突，采用“任何恶意标签即成员”的集合并集口径；早期错误的首行标签缓存和结果保存在`cache/url_first_label_invalid`与`results/invalid_url_first_label`，没有混入最终表。Shalla与完整URL均独立训练本轮模型。所有训练负例、验证负例、测试负例交集为零。

## 2. 主结果与对网格的判断

在940个合成负载/种子/预算配对中，StreamModel的FP少于LearnGrid有137个、多于有645个、相等有158个。这是描述性计数，不是独立数据集数量。下表合计各预声明负载的FP，包含不同长度once/fresh；比例仅便于定位异常，正式比较应查逐负载均值、区间和配对差，不能作为跨负载显著性或上线收益。

|数据|KiB|案例数|Gama FP合计|模型 FP合计|网格 FP合计|(模型+1)/(网格+1)|
|---|---|---|---|---|---|---|
|caida|128|100|39804398|24012734|22227780|1.080|
|caida|256|100|20517059|7810510|7108980|1.099|
|caida|1024|100|6244995|121776|72022|1.691|
|caida_flow|16|1|2181215|2181215|606231|3.598|
|caida_flow|24|1|1670193|1670193|394371|4.235|
|caida_flow|32|1|1380973|363340|284969|1.275|
|cod|256|80|9522290|580756|518746|1.120|
|cod|1024|80|3825520|213633|1809|118.030|
|mawi2021_flow|16|1|627712|45229|40546|1.115|
|mawi2021_flow|24|1|267742|11938|9565|1.248|
|mawi2021_flow|32|1|138076|3483|2680|1.300|
|mawi2022_flow|16|1|349066|71023|71023|1.000|
|mawi2022_flow|24|1|157145|22765|20708|1.099|
|mawi2022_flow|32|1|122496|12895|6454|1.998|
|shalla|256|80|115753657|45731187|40149042|1.139|
|shalla|1024|80|38786401|3797031|3531085|1.075|
|shalla|2048|80|11066824|508006|396547|1.281|
|url|64|80|6011041|370499|296592|1.249|
|url|128|80|4242229|130808|3924|33.327|
|url|256|80|3762751|3059|132|23.008|

COD1024、URL128/256的模型/网格差距尤其明显，不能以少量高重复场景代替全矩阵。当前可保留“负缓存处理重复误报”的方向，但贡献3既不能写效果更好，也不能未经新证据写为5KB达到网格效果。A2的top3/5/10实际结果另列，用于判断有限回放是否值得；不把其结果反馈到已固定主方法。

|真实轨迹|KiB|方法|尾段FP|FPR|树数|比例|
|---|---|---|---|---|---|---|
|caida_flow|16|Gama|2181215|50.3530%|4|0.0|
|caida_flow|16|StreamModel|2181215|50.3530%|4|0.0|
|caida_flow|16|LearnGrid|606231|13.9947%|4|0.4|
|caida_flow|24|Gama|1670193|38.5561%|4|0.0|
|caida_flow|24|StreamModel|1670193|38.5561%|4|0.0|
|caida_flow|24|LearnGrid|394371|9.1040%|4|0.6|
|caida_flow|32|Gama|1380973|31.8795%|4|0.0|
|caida_flow|32|StreamModel|363340|8.3876%|4|0.1|
|caida_flow|32|LearnGrid|284969|6.5785%|4|0.4|
|mawi2021_flow|16|Gama|627712|24.4053%|1|0.0|
|mawi2021_flow|16|StreamModel|45229|1.7585%|1|0.4|
|mawi2021_flow|16|LearnGrid|40546|1.5764%|1|0.2|
|mawi2021_flow|24|Gama|267742|10.4098%|1|0.0|
|mawi2021_flow|24|StreamModel|11938|0.4641%|1|0.3|
|mawi2021_flow|24|LearnGrid|9565|0.3719%|1|0.2|
|mawi2021_flow|32|Gama|138076|5.3684%|1|0.0|
|mawi2021_flow|32|StreamModel|3483|0.1354%|1|0.2|
|mawi2021_flow|32|LearnGrid|2680|0.1042%|1|0.05|
|mawi2022_flow|16|Gama|349066|15.6966%|1|0.0|
|mawi2022_flow|16|StreamModel|71023|3.1937%|1|0.2|
|mawi2022_flow|16|LearnGrid|71023|3.1937%|1|0.2|
|mawi2022_flow|24|Gama|157145|7.0664%|1|0.0|
|mawi2022_flow|24|StreamModel|22765|1.0237%|1|0.3|
|mawi2022_flow|24|LearnGrid|20708|0.9312%|1|0.2|
|mawi2022_flow|32|Gama|122496|5.5083%|1|0.0|
|mawi2022_flow|32|StreamModel|12895|0.5799%|1|0.4|
|mawi2022_flow|32|LearnGrid|6454|0.2902%|1|0.1|

五种子的95%t区间是固定数据/固定模型下工作负载种子的不确定性；配对检验使用32种符号翻转，双侧最小p=.0625，因此不能在.05下声称显著。主比较族按预定范围Holm校正；fresh为确定序列，有效独立重复数1，不制造区间。真实轨迹同样仅描述，hash盐敏感性150条另表，不把5个hash当5条独立轨迹。

## 3. 内存口径与基线

Gama部署不扣5,128B草图；所有方法完成学习后都不保留草图。缓存采用word-packed quotient前缀布局，真实数组头、格式头、空槽、CLOCK/LRU/FIFO元数据均计费；缓存定额未用部分返还BF。此口径为实际部署数组与规定描述符，执行器包装对象、JIT和输入数据归宿主基础设施，不等于整个Python对象图。逐条组件和始终小于等于预算由核验脚本检查。每个实际选择的缓存容量、空槽、已用槽、每槽实测字节及返还BF字节另列于`tables/cache_allocation_audit.csv`；不继续沿用28bit/条的理想编码假设。

**KiB预算是过滤器部署状态预算，不是整个进程或全系统RAM。** 已校验缓存额外需要8×成员数+112B数组头的有序成员hash索引；Gama、静态Stacked不需要该索引。表中同时保留仿真进程统一分配的索引和方法必需索引。学习网格保留轨迹，模型统计payload5,128B外还有数组头、公共模型候选、数据、JIT等；观测到整进程最大RSS为8.59GiB，不能宣传整段学习仅5KB。`tables/selection_costs_current_grid.csv`用更新后的精确加速网格与模型并列计时；早期主实验较慢网格计时只作原始记录，不能用于夸大必要成本。

下表固定展示各数据第一主预算、uniform1万池、seed0的模型选择；不是所有设置的平均。小缓存的格式头和数组头摊销很高；已用条目成本还会随占用率升高。完整表逐行保留所有选择与空槽。

|数据|KiB|缓存B|预留槽数|B/槽(含头和空槽)|必要校验索引B|
|---|---|---|---|---|---|
|caida|128|5328|1024|5.203|9569664|
|cod|256|504|64|7.875|24000112|
|shalla|256|19856|4096|4.848|23413752|
|url|64|504|64|7.875|1704472|

真正普通BF+negative cache使用同一已校验缓存，在学习期调比例；Fixed48Grid明确只是固定48树的消融；SkiQFAdmission2是计费的二次准入实现，不冒充整篇SkiQF。Learned stacked以Gama验证选中的树数为底座，在学习期内部一半构建、一半选侧层比例与b2，最后用全部学习期重建，并加入零侧层退化选项，旧结果重新比较不接触尾段。

原版Stacked历史审计共913条，其中716条超标，按旧实现内部记账反推的倍率逐条列于`tables/historical_stacked_memory.csv`；这是清单B2允许的标注路径，超预算历史数据不混入本轮严格预算排名。AdaptiveQF为上游C实现，经WSL原生编译实际运行342条，报告malloc实际分配和反查表；低预算是否连最小结构都装不下见`results/aqf_preflight.json`，高预算结果与同预算Gama同流比较，不能与低预算主表偷换比较。

B6按清单的说明路径完成：本轮复现为14个前缀树数搜索、100段PLBF、位打包实测状态，而原作者Hybrid用其独立搜索流程与pickle口径。详见`evidence/B6-gama-reproduction.md`。不能声称逐字复现原作者Hybrid的数字或调参时间。

学习调优Stacked与模型的196个负载/预算均值比较中，模型更差142个、更好44个，相等10个，同样不构成稳定优势。Stacked允许把学习期观察到的负例构建为部署BF；缓存方法按本协议在尾段冷启动。这种知识携带方式属于各自算法，选择与建层均不使用评估尾段。完整区间/配对差在主表，而非只展示模型胜出的设置。

|AQF数据|KiB|案例数|AQF FP合计|同预算Gama FP合计|AQF堆状态最大B|反查表堆分配最大B|
|---|---|---|---|---|---|---|
|caida|2048|100|3705161|3776489|1882824|78566256|
|caida_flow|256|1|6723|16989|240024|13818256|
|cod|4096|80|1199076|3692876|3756024|197773872|
|mawi2021_flow|128|1|32|0|130728|2660344|
|shalla|4096|80|952133|4090970|3756024|193669368|
|url|256|80|559598|3762751|240024|13982616|

这里仍是混合长度负载的描述性合计；高预算和主表低预算不混排。反查表列是实际堆分配，Map包装本身以及宿主程序基础设施另属运行时对象，不能把这列冒充全进程内存。

## 4. MAWI旧标题数字审计

|扣草图B|KiB|树数|误报总量|不同误报key|最热key占比|
|---|---|---|---|---|---|
|5128|40|4|107|37|16.8%|
|5128|48|4|70|15|34.3%|
|5128|64|4|299|1|100.0%|
|0|40|4|63|17|38.1%|
|0|48|4|198|12|89.4%|
|0|64|4|4|2|50.0%|

旧64KiB的299次FP全部来自一个BF热点。取消不应向Gama扣的草图后，同预算剩4次FP、2个key；旧“77倍”标题数字应撤回。BF位数与取模改变会换一批误报key，真实流按频率加权后的误报量不保证随预算单调；这不等于训练或测试数据相交。

## 5. 真实推理与实际KV后端

E1共80条路径，每条3次冷缓存尾段计时，COD256/1024、Caida128/256，10%/50%正查询、uniform/Zipf两类。执行hash、实时树遍历、BF、缓存、成员前缀校验与负反馈，原始分数与LightGBM最大误差小于1e-10；特征提取和输入I/O不在计时内。前置和后置用各方法自己的学习期选择配置，不能借用不匹配的FPR主表配置。1/10/100微秒后端是`CPU时间+真实访问率×设定延迟`的明确投影，不是实际磁盘测量。原始重复时长、命中、推理和后端访问次数均保留。

|方法|缓存位置|1us后端速度比中位数|10us|100us|
|---|---|---|---|---|
|StreamModel|before|0.979|0.991|0.999|
|StreamModel|after|0.995|0.998|1.001|
|LearnGrid|before|0.962|0.978|0.998|
|LearnGrid|after|0.991|0.994|0.999|

速度比以同场景Gama为1，跨16场景的中位数只作描述；总体未体现普遍加速，接近1的计时差不能据3次重复宣称显著。FPR改善不能直接等同于吞吐净收益。

E2采用真实SQLite文件KV、同步SELECT、8MiB页缓存、mmap关闭，未刷新OS页缓存。每条评估100,000次请求、3轮轮转顺序，包含Python/Numba/SQL调度成本；不是冷盘延迟，也不能直接与E1融合内核的CPU单价互换。

|方法|每次查询ns中位数|实际get次数/10万|实际miss次数|重复|
|---|---|---|---|---|
|NoFilter|36202.2|100000|89984|3|
|Gama|11729.9|10130|114|3|
|StreamModel|11954.9|10058|42|3|
|LearnGrid|9901.7|10047|31|3|

## 6. 消融与动态行为

A1所有5/10/25/50%学习前缀统一在同一最后50%冷窗口评价，间隙不用于预热；旧可变窗口结果另存。A2是模型排名中不同物理布局top3/5/10后精确回放；A3包括同布局CLOCK/桶FIFO、全局LRU/FIFO控制，跨前缀编码与full-hash实现的容量不同，不声称纯替换策略的因果效果；A6完整4种前缀×3种ways，以及细分0–2%比例网格。

|24KiB真实流|纯模型FP|top3 FP|top5 FP|top10 FP|全网格FP|
|---|---|---|---|---|---|
|caida_flow|1670193|731230|552503|418168|394371|
|mawi2021_flow|11938|11938|9565|9565|9565|

top-k在部分失败例能明显降低观测误报量，但不据这两条轨迹宣布普遍等价。A2原始计时保存共享top10回放总成本，没有把这个总时长假装成单独top3或top5成本。Caida_flow24的纯模型选了零缓存，所以该点A3/A4的相等结果是配置退化，不是替换策略或key编码等价的证据。其它预声明设置与受控fixture照常保留。各消融的均值、标准差和95%t区间见`tables/ablation_metrics.csv`，真实单条轨迹不做区间。

A4中COD/Caida原始scalar64经双射hash，64位全hash本来就是精确标识；URL/flow无限原始键空间的预hash才有碰撞概率。真实数据未观察到碰撞，另用注入相同预hash的fixture证明：已校验前缀绕过不能安全缓存的负例，不校验64位缓存会误拒成员。这不是自然碰撞发生率测量。

O5在真实URL键上顺序增加1000个成员，先失效冲突缓存，再更新BF及索引，最后发布成员；实际移除358条缓存记录，214045次最终成员检查及在线查询均0FN。失效中位数1700ns、p95 3100ns；排序索引维护中位数435550ns另报。此测试不证明并发原子发布或崩溃恢复。

O6在漂移流50/75%处仅用过去四分之一窗口批量校准，保留20MB轨迹，临时草图和原子替换新旧状态并集另计；不是恒定5KB在线更新，不是全程相同峰值内存。

|数据|冻结FP合计(5种子)|周期FP合计|校准+重建s合计|替换状态峰值B|
|---|---|---|---|---|
|cod|270536|270536|2.719|262144|
|caida|12470300|11913811|7.287|196879|

## 7. 独立验证和保留边界

MAWI2022-04-13固定前120,000,000压缩字节，下载后未训练/查看模型指标，最终执行代码与协议SHA先写入`plan/final-holdout-freeze.json`，之后才首次准备、训练并评价16/24/32KiB和学习Stacked。没有根据其结果回调参数，冻结后hash未变。数据是固定前缀而非整天全流量。

这是冻结方法在新数据划分上的一次评价，按同一协议在2022划分的训练/验证部分学习模型并选配置；不是把2021训练的模型直接迁移到2022，也不是无标签的新日在线评估。新数据未用于外层设计选择的保证限于本轮可核验的本地记录。

**保留的实现失败：** MAWI2022的学习Stacked16KiB在内层半学习验证中选出的侧层，使用全部学习期负例重建后无法放进预算；冻结实现此时返回失败，未走文档所述零侧层退化分支。这是该实现的鲁棒性缺陷，不能解释成所有Stacked方案都不可行，更不能记为零误报。24/32KiB照常成功；该失败已计入核验JSON与任务表，没有修改冻结代码、补跑留出或把Gama结果冒充一次成功的Stacked测量。后续若修复，应在另一份独立留出上重新验证。

flow成员集合由协议离线定义；地址特征不使用整段聚合，但原始包本身含协议时，应用能直接区分UDP/TCP。因此它是静态成员集合/不透明key压力测试，不能据此声称完整在线网络分类方案的必要性或普遍净收益。

## 8. 完整性与逐项证据

源工作簿SHA256：`b9aaf732de7cd16abfb09328ae04ada952a603d54987e938c437836af93d4183`，原件未写入。`research/`与`learned_adaptive_hybrid/`共8,018文件、27,383,286,883字节，内容hash与修改时间均与本轮开始前一致。失败和被纠正的数据/调度尝试保留在evidence，未用删除失败重试来声称零重启。新代码、结果、表格、原始日志及模型hash全部在本轮目录，并按用户明确要求提交到现有GitHub仓库；本轮提交范围仅round2_backlog，原research、数据/缓存、临时文件和外部源码检出未加入提交。

|任务|状态|证据|限定|
|---|---|---|---|
|F1 Gama 不扣草图|completed|results/main; tables/main_metrics.csv||
|F2 修正 CLOCK 分桶浪费|completed|results/main（cache_returned_bytes）||
|F3 “TODS 式”改名|completed|results/main（Fixed48Grid）||
|F4 MAWI 倍数复核|completed|results/F4_mawi_hotspots.json||
|M1 恢复完整规模|completed|results/main; results/verification.json||
|M2 加回 Shalla、加入 URL|completed|cache/url/preparation.json; cache/shalla/preparation.json; data/*-source.json||
|M3 统计显著性|completed|tables/main_metrics.csv; tables/paired_comparisons.csv; tables/aqf_metrics.csv||
|B1 learned stacked 改为学习期调参|executed_with_recorded_failure|results/stacked; tables/main_metrics.csv|；MAWI2022的Stacked16KiB冻结实现重建失败，原样保留、不补跑，也不据此宣称优于该基线|
|B2 原版 Stacked 压回预算|completed|tables/historical_stacked_memory.csv|采用清单允许的倍率标注方案；由原实现内部记账反推，非本轮物理堆内存；旧超预算结果不进入严格同预算排名|
|B3 AQF 用真实实现重跑|completed|results/aqf; results/aqf_preflight.json; tables/aqf_metrics.csv||
|B4 SkiQF 准入重跑|completed|results/main（SkiQFAdmission2）||
|B5 真正的 TODS-CAF|completed|results/main（BFCacheGrid）||
|B6 原版 Gama 代码选树数|completed|evidence/B6-gama-reproduction.md|采用清单允许的明确说明复现方式方案；并非逐字复现原作者Hybrid|
|E1 和 Gama 对比吞吐|completed|results/live; tables/live_projected_speedups.csv|C臂按用户要求排除；后端延迟为投影|
|E2 真实后端实测一个点|completed|results/sqlite_backend.json; tables/sqlite_metrics.csv|实际SQLite文件KV，OS缓存未清空|
|R1 特征不看未来|completed|cache/*_flow/preparation.json; results/verification.json||
|R2 至少两条、预算有区分度|completed|results/main/caida_flow; results/main/mawi2021_flow; results/hash_sensitivity||
|R3 最终独立验证|executed_with_recorded_failure|plan/final-holdout-freeze.json; results/main/mawi2022_flow; results/stacked/mawi2022_flow|首次训练/评估前冻结执行代码；只报告固定日期固定配置；MAWI2022的Stacked16KiB冻结实现重建失败，原样保留、不补跑，也不据此宣称优于该基线|
|A1 学习期长度|completed|results/ablations; evidence/A1-original-variable-windows||
|A2 选择器剪枝|completed|results/ablations（A2）||
|A3 淘汰策略|completed|results/ablations（A3）|两组同布局控制及跨编码实现敏感性，不能混为纯替换策略差异|
|A4 成员校验|completed|results/ablations（A4）; evidence/A4-injected-prehash-collision.json||
|A5 缓存位置|completed|results/live（before/after）||
|A6 实现参数|completed|results/ablations（A6）||
|O5 动态插入成员|completed|results/dynamic_members.json|顺序发布正确性，不覆盖并发原子性|
|O6 定期重新校准|completed|results/recalibration_cod.json; results/recalibration_caida.json|使用过去窗口20MB轨迹；重建双状态峰值另报|

核验入口：`src/verify_round2.py`；结果`results/verification.json`。汇总入口`src/summarize_main.py`，报告入口`src/build_report.py`，绘图入口`src/make_figures.py`。候选构建共享成本、旧/新网格实现时间、部署/索引/学习/重建峰值均不混写。

结果图：[真实流FPR](figures/causal_trace_fpr.png)、[模型与网格FP](figures/model_grid_fp.png)、[端到端成本](figures/end_to_end.png)；同名SVG为矢量版本，源数据及图说明见`figures/data-manifest.md`。

主实验推进中存在已验证数值等价的实现加速和明确记录的修补，不能声称全研究过程始终使用同一冻结版本；严格的事前执行代码/协议冻结仅针对最终MAWI2022留出。最终源与模型/结果SHA保存在evidence中，以当前代码复现的时间开销应采用当前实现，不套用早期冗余版本的日志时间。

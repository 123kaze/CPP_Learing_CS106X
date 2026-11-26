# 第54轮：审查补充实验固定协议（首次运行前）

2026-11-25。承接`docs/审查补充实验_TODO_20261125.md`。本轮分模块执行，不覆盖旧轮次、不改论文、不自动push。只用本地已验证输入。

## 资源与计费

用户授权删除冗余SIS分块和旧超时残片，完整包/完整五月文件重新校验保留，清理回执独立保存。实测清理后空闲8162430976B（7.60GiB），未达到预估8GiB。为**本批无新大数据下载/解压、输出上限512MiB**的新协议登记磁盘保留4GiB，非复活旧8GiB门限失败实验；RSS仍严格4GiB、单worker/单线程，每模块1800秒（online模块3600秒），内存中止不自动重启。数值优化及模拟均计时，JIT单列。

## A. 四本账与1076统计（仅复算旧记录）

- 第53轮全部62case/434行：部署M及实占、所需部署成员验证索引0、前缀旧方案假设索引8n+header单列、learning key/count/rate真实数组payload+header、共享进程peak RSS。RSS无法分摊到方法时明确标为worker共享峰值，不虚构每方法独占峰值；既有失败峰值保留。
- 第19轮GT19修正后所有1076非probe case，index/fp64分别对Gama、Replay、BF+Cache计算逐例绝对FP差、每百万查询差、平滑配对比；纳入FP<30，不按结果改cohort。
- dataset为cluster：先每dataset平均，再8个dataset等权，固定seed5401、20000次cluster bootstrap给95%百分位区间。真实流另列原固定4个dataset；样本cluster少，区间是描述性，不是独立应用推广或等价性证明，不重新追p值。
- 已有GT19十四case、零树第17/20轮、时间边界/理论边界核验可明确复用；不称新运行。Eq10用实际P.at_capacity/solve检查饱和与T_grid_max=1000H，不声称精确物理TTL。

## B. 零树候选与重加权全Replay

共31case：TCP-only四原数据×原四预算16case；ClarkNet seeds3601/3602/3603×8/16/32KiB 9case；URL seed0×64/128/256KiB×原once/fresh生成流6case。原fresh/once仍按冻结生成规则（10M上限参数，once不截断），learning前25%、cold tail后75%。

所有方法使用同一无索引完整key CLOCK（复用第53轮schema；TCP原key不含Label，CAIDA32bytes、MAWI8bytes），相同预算；新零树方法明确另名：
- Gama；原RA6-GT19；13份额BF+Exact学习Replay；h权重Replay；
- RA6-Z-predictive：第17轮原规则，0树与learned预测候选并集，整体top5，桶精炼；
- RA6-ZGate：RA finalist与BF学习winner精确learning回放比较，tie选BF（不是直接把0加进列表即可no-regret）；
- RA-weighted-ZReplay：完整RA加权候选＋13零树候选在learning精确回放，作为较贵扩展，不继承49×或无重复Gama性质。

完整重加权Replay只在C模块6个固定case执行；B模块31case报告上述前六方法（186行），不为节省算力冒称31case都已搜加权全网格。Clark新训练原200trees/同seed，旧URL/TCP固定模型不重训；学习回放是离线labels参考，不冒称新线上更新机制。

## C. 耦合参考、Stage1/Stage2分解、同频不同序

固定6case：URL64/128KiB，MAWI24 16/32KiB，ClarkNet seed3601 8/16KiB。树前缀与cache份额为原完整网格；不按tail筛参数。

- 对RA.candidate_table全部加权候选实体构建＋learning Replay；对h权重全部候选同样学习Replay。并列Gama、h-Replay、RA-stage1、RA-stage2(top5)、RA-weighted-Replay、BF+Exact、RA-weighted-ZReplay，记录完整候选learning/tailFP及成本。all-tail仅作离线诊断，不影响选择。
- 同频不同序：分别对learning和tail应用original、固定seed5401 shuffled、按key连续块bursty、按key轮询cyclic；每key频数逐项一致，绝不跨窗口移动key。频率预测应逐位相同（同H），h/weighted/BF的learning Replay需按新顺序重新选择；RA阶段选择应不受排列影响。保留所有query包括static reject，报告cache状态/FP/FN。
- 收敛分析：每case固定Gama树、10%cache的分区/成员数/预算，将负例population聚合到实际至多5个region。原P.solve的0/1/2/3/5/10/20轮精确复算；再多算一步获取真正残差，不以第3和第2目标相近冒称fixed point。记录epsilon无穷范数、等效全相联T及饱和状态、目标相对变化、二周期迹象，阈值epsilon1e-6与目标1e-6事前固定。
- 耦合数值参考分两目标：(i)原161点T网格＋Poisson SA耦合目标；(ii)直接按分组频率用70步二分解Che容量的全相联目标（未填满以T=1000H为明确有限窗口上限）。以bits shares参数化确保BF bit约束，零member EMPTY固定0；固定coarse simplex分母12＋SLSQP多起点（uniform、h、原3轮、coarse最好、seed5401三随机，共7起点），ftol1e-10、maxiter300。报告每次优化成功/失败与可行性，不隐藏更差局部点；best observed feasible不称全局最优。两目标的gap分开，不拿一个目标优化值给另一个充当最优。

## D. 实际raw-query执行与正比例/成本扫描

代表性固定配置：URL128KiB seed0、MAWI24 32KiB seed0、ClarkNet16KiB seed3601、SIS1343KiB seed5001 balanced_clip。所有方法同exact cache；Gama、Replay、RA-global、RA6、BF+Exact、PlainBF、NoFilter，7方法。

- 各5000条总查询，member比例10%/50%/90%/99%，member从成员池固定均匀抽样（不是原自然正query频率），negative取原tail前缀按原顺序；不足则预先固定循环，不按FP挑键。成员位置固定seed5401打散，共4×4×3×7×3=1008计时窗口。
- 后端为**本机精确raw-key集合服务替身**，不是生产DB：完整byte-key membership查找与value32B返回/None反馈，加numba单调时钟spin到每lookup目标3/37/100微秒（实际可能超标）。按目标记录校准分布和实际整窗，不能称真实跨机RTT或把目标值当实测值。NoFilter跳过不必要hash/features/model；所有filter做rawkey hash、必要feature生成、实体模型/BF、cache查找及精确negative反馈，严禁从预计算flags驱动计时。
- URL原hash用pandas官方单字符串hash保持旧ids；词法18feature用等价Python字符串/regex实现，完整池或固定分块逐行校验与旧X。流从完整原tuple解码两个float32特征；Clark/SIS沿用真实URL20feature与SHA256身份哈希。若推理或特征与旧flags不符，停止，不静默容忍。
- 每方法每窗口mask/count/cache SHA与离线参考逐项一致；混合所有member不得FN。先单独JIT+验证，不把JIT混入热query时间。
- 报告平均时延/吞吐、3重复中位和范围、单次call实际服务成本校准、固定比例时延盈亏；启动成本分新训与复用，缺测训练不填0或伪造完整构建。Clark/SIS本轮重训计时，URL/MAWI复用已有训练只报load-to-ready；历史训练耗时只作明确标识参考。
- SIS99.84%自然比例不能由人工99%直接替代；额外登记p=0.9984一组（3成本×7方法×3rep=63窗）作为比例匹配**重采样**，不称原自然流。自然rawquery时序未恢复时必须保留此限制。

## E. 验收

B186行、C168方法行（6case×4order×7方法）及全部候选明细、收敛/数值参考、D1071计时窗口、A434资源＋1076×2绝对统计。分别输出源码/输入SHA、资源/失败记录、unit tests、全部CSV/JSON与中文README；每项通过后更新TODO。任何模块不完整不得标记总任务完成。

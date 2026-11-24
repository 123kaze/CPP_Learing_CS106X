# Round52：SIS完整文件首次实体filter比较（新训练配方与原配方并列）

2026-11-24。用户要求继续实验。第51轮预选balanced_clip在3/3seed通过开发闸门，开发AUC中位0.979355（原配方0.420383）；仅开发结果，不是filter胜出。SIS文件已做过inventory/开发探索，不是独立holdout。原第48轮prefix失败不改。

## 固定矩阵

recipes={original,balanced_clip}；seeds5001/5002/5003；ceil(2749058*{2,4,8}/8192)KiB={672,1343,2685}。18case keys，各Gama、Replay、RA-global、RA6-Exact128、BF+Exact128、PlainBF、ZGate，共126主行。所有learned方法在同一recipe使用同一个训练模型和20query-only词法特征，BF不付不需要的训练成本。两个recipe的BF/PlainBF配置、FP、flags/cache必须逐case完全一致。

固定200boost rounds/31leaves/lr.1；balanced_clip使用第51轮固定weights和max_delta_step1。14个原tree-prefix/13cache-fraction网格。若训练本身提前停止，只有<=实际tree数的原网格前缀可用，未训练前缀明确infeasible、不补造树；同recipe所有learned方法使用同一可行集。RA6候选表仅在作用域内转发此可行tree集合，公式/DP/Top5/GT19/CLOCK不改，finally恢复绑定。该可行性规则在首次200tree训练和实体FP之前冻结。

沿用完整文件静态observed-success/404稳定子集与第50轮split、原负流顺序；H=预声明真实tailnegative数。训练/val负key不进入评估池；seed5002因heldoutkey划分移除了主要热点，评估负请求显著少于其他seed，此差异不隐藏、不删除该seed。记录保留请求比例及学习/tail未见质量，不能把3seed说成3独立工作负载。

## 严格cache及预算

Exact128完整rawtarget bytes，长度>128绕过，不截断、不用hash作为精确身份，不持有验证成员索引。全部模型/BF/routing/header/cache字节计入相同Filter Budget。Fullmember静态BF检查与最终cache0FN检查；完整负流coldtail回放，staticreject queries也做cache lookup。记录长key比例/请求比例；冻结RA预测未单独建模长keybypass，这是模型限制，不因结果改规则。

cache方法返回学到的真正结构；ZGate仅比较RAfinalist与BF学习回放赢家，tie选BF，额外回放/两类搜索成本全计，不继承未来不退化或49×。没有改变原Gama/RA6已发布结果。

## 权重机制控制

每case固定validation预测最小FPR的10%cache anchor，保持trees/partition/实际members/BFbits/cache/hash不变，仅h/traffic/miss三种capped连续分配+整数物理BF。18×3=54行，原round37 mass recipe复用；使用Exact128真实回放。正支持/双内点AMGM条件与actual CLOCK非外生T分开，不把实体结果当定理全称保证。

## 分项计时与边界

准备/加载、weights、200tree训练、chunked pred_leaf多prefix评分（32768rows块）、模型数组、共享tree-segment准备、GT/JIT、候选构建/选择、权重controls构建、tail replay和全member cache核验分别计时。沿用已冻结leaf_scores，不分配N×200全leaf矩阵。峰值RSS与输入rawblob/X/score arrays单列，不当Filter Budget。

本轮不测SQL、rawfeature服务时间或远程部署；不能用负流FP改善替代整体时间回本。全文件原negative比例约0.16%，正query压倒多数，这一部署限制保留。

## 执行与验证

小型synthetic fixture验证：原grid转发/异常恢复、balancedclip rawscore界、精确cache/hashalias、物理预算/成员检查。全部source及prepared/开发回执SHA冻结后执行。

Pilot固定balanced_clip/seed5001/672KiB一个case（全量catalogue与原完整tail），单独目录/记录且不计入正式矩阵，只按资源/时间门限：预测正式6worker×3budget整体<=7200秒、peakRSS<4GiB，至少8GiB空闲。不同方法胜负/AUC不作gate。通过后6个worker顺序单线程，每worker1200秒/RSS4GiB，无自动重试。Formal重选/重建，匹配pilot非计时输出；全部负结果和失败日志留档，不看tail改模型/流/预算。

首次实体FP结果全部公开聚合，rawURL/身份不发布。论文不改，不自动push，不开subagent。

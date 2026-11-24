# Round50：SIS完整已观测文件的开发诊断（探索，不是独立holdout）

2026-11-23。第48轮固定prefix资格失败不变；第49轮完整扫描后知悉基本规模达标（2749058members/3467negativekeys/63377稳定404），实际文件2018-05-23至31日，不是完整日历月。本轮明确为后续探索，已见文件规模，不声称新独立数据。

## 数据与split冻结

仅使用第49轮精确SQLite inventory和同一已校验五月源文件，不新下载/读取其他月份。采用全部回溯稳定observed-success/404 target keys（flags1/2），冲突flags3排除。原querystring不剥离，status/client/日期/未来频率不是特征。

从只读SQLite按k字节序流式生成ids、y、20个旧词法特征、first_GET_order、完整raw-key blob/offsets及cheap path支持规则，避免把数百万raw keys同时放Python字典。SHA64ID只作旧BF引擎输入，有限集合唯一性assert；若后续负cache使用，仍须Exact128完整key匹配。

重扫原source一次，只恢复稳定negative的原始有序query stream及GET ordinal；成员请求不改变精确negative cache状态，因此本轮不存所有positive request数组，不声称已做端到端查询。EOF行数/GET数/全sourceSHA必须重现第49轮，原序列不重采样。原文件前25%GET ordinal作为development/learning边界。

seeds5001/5002/5003（新探索种子，不覆盖旧4801组），member哈希50%train；仅early negative keys按10%train/10%val，其余query pool，保持key互斥。固定16tree/31leaf/lr.1/单线程，**不改class weights、采样比例或score方向来追AUC**。训练/验证样本量不足仍如实标记，不跑方法FP。模型实际tree数、开发AUC、完整特征重叠、score1000segment占用/饱和、学习重复/region重复差、tail出现的新key请求比例均报告。

说明：正负训练样本数量可能极不平衡，AUC与score量化可用性是不同诊断；本轮不改变旧sigmoid/segment规则。若将来研究重采样/校准，必须另标新变体，同样给所有learned基线，不改旧结果。

## 资格

原基本门限保持members>=10000、negativekeys>=1000、稳定404>=10000、保留>=90%；每seednegtrain/val>=20、learning/tail query-pool negatives>=1000。AUC>=.70/overlap>=.01/repeat>=.10/两区50distinct且gap>=.10只作解释，不基于RA胜负筛选。方法选择/FP/端到端尚未执行。

## 资源和时间

每次单worker，不并行训练。准备1800秒，diagnostic每seed600秒，RSS4GiB，prepared文件/工作区最多4GiB、至少8GiB可用磁盘。输入raw-key准备和计数是offline工作区，不能藏入Filter Budget。parser/词法/计数/训练/评分/overlap/检查分别记录。

全部源码和输入metadata/DBSHA在首次本轮准备/训练前冻结；原DB只读，rawprivate URLs/client不发布，不execute data。超时/内存失败留档，不自动重启。当前只诊断，不宣布正结果，不修改论文/push。

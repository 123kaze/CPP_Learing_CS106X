# Round49：完整五月文件规模清点（探索已完成，基本规模达标）

[协议](plan/design-freeze.md) · [源码冻结](plan/freeze.json)

第48轮固定前2000000行未通过资格，结论不变。此轮是明确的后续探索：扫描整份已校验五月文件到EOF，而不是尝试不同小窗口找赢家。它包含已见prefix，因此不是独立holdout，也不能把全月规模结果倒填为第48轮通过。

不训练、不测方法FP、不调特征/预算；只统计全部GET/status、完整target的success/404/conflict、原日期/顺序、频数分布与基本规模。磁盘SQLite是离线计数工作区，不是应用backend性能证据。

3项SQL聚合/跨batch冲突/参数身份测试通过后冻结。单进程/单线程，1800秒、RSS4GiB、DB8GiB、至少保留8GiB空闲。目标完整13687894566B，扫描SHA须匹配原完整文件；到第2000000行先逐项复现第48轮计数/前缀SHA，再继续EOF。

原第48轮失败、原解压超时及部分文件保持；没有新增下载或解压，也未打开其他月份。原始URL/client不发布，ignored DB不视为可公开结果。只有completion/inventory标complete才表示清点结束；过程中的DB和progress不算完整证据。

## 已核验结果

[完整清点](results/inventory.json) · [前200万行回归](results/prefix_regression.json) · [独立核验](../../docs/round49_evidence_20261123/verification.json)

全文件41714245行、40783531个GET，源SHA完全匹配，耗时258.90秒、峰值RSS194723840B，offline计数DB497414144B。前2000000行与第48轮的所有关键计数、状态计数及prefixSHA一致。

- 稳定members2749058、negativekeys3467；冲突keys9。
- 原40463388次，保留63377次、排除冲突40411次，保留99.98265%。基本全文件规模门限通过。
- 但9个高频negativekeys贡献57698次请求（约91.0%）；另有2799个negativekeys只出现一次。缓存与冷新key的角色需要区分。
- 实际文件覆盖2018-05-23 04:32:03至05-31 04:17:01（+0200），1303次时间回退，不是完整日历月。原始GET中404日比例从约0.42%下降到约0.016%；首尾日不完整，不把这个流视为已证明平稳。
- 独立读取DB验证count、frequency bins、first/last ordinal、日期状态总计及SQLite quick_check通过，未改旧数据库/结果。

这只证明全文件基本规模达到门槛，还没有训练/验证数据资格、AUC、模型价值或真实部署收益。后续另冻[第50轮开发诊断](../round50_sis_fullfile_diagnostics/plan/design-freeze.md)，披露本次完整扫描已发生；它仍不是独立holdout。原第48轮失败不变。论文未动，未push。

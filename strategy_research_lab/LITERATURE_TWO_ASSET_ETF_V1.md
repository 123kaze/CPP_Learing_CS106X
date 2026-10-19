# 两资产 ETF v1：文献证据与边界

核验日期：2026-10-12。检索先通过 OpenAlex 发现候选，再以 Crossref 的 DOI 元数据逐条核验
题名、作者、期刊与年份。下列论文提供的是**可检验的经济机制或反证理由**，不是对 510300、
518880、50/50 权重或未来盈利的背书。

## 与冻结规则直接相关的证据

| 论文 | 可支持的研究动机 | 明确不能推出的结论 |
|---|---|---|
| Baur & Lucey (2010), [*Is Gold a Hedge or a Safe Haven? An Analysis of Stocks, Bonds and Gold*](https://doi.org/10.1111/j.1540-6288.2010.00244.x) | 在股票、债券与黄金之间区分“对冲”和“避险”性质；支持把黄金视为值得检验的分散化来源。 | 不证明中国黄金 ETF 在任何时期都与沪深 300 负相关，亦不证明 50/50 配置会赚钱。 |
| Bekiros et al. (2017), [*Black swan events and safe havens: The role of gold in globally integrated emerging markets*](https://doi.org/10.1016/j.jimonfin.2017.02.010) | 将黄金在新兴市场极端情形下的避险作用作为实证问题研究。 | 极端行情定义、市场结构和交易工具不同；不能外推为 A 股 ETF 的无条件保护。 |
| Chkili (2016), [*Dynamic correlations and hedging effectiveness between gold and stock markets: Evidence for BRICS countries*](https://doi.org/10.1016/j.ribaf.2016.03.005) | 说明股票—黄金相关性与对冲效力具有动态性，支持同时报告回撤而不是仅报告平均收益。 | 不支持假设相关性恒定，或据此选择一个历史上最优的再平衡频率。 |
| Roncalli & Weisang (2015), [*Risk parity portfolios with risk factors*](https://doi.org/10.1080/14697688.2015.1046907) | 说明跨资产配置应明确风险来源与集中度，而不应只看单资产收益曲线。 | 当前策略是受 2 万元和整手约束的**等资金**配置，不是风险平价，不能冒称为 risk parity。 |
| DeMiguel, Garlappi & Uppal (2007), [*Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?*](https://doi.org/10.1093/rfs/hhm075) | 对估计误差和复杂权重优化保持警惕，支持把简单、可执行、预先固定的配置作为对照。 | 不代表任意简单规则优于优化，也不证明 50/50 在本市场最优。 |

## 反证与未采用的波动率调仓

| 论文 | 对本项目的含义 |
|---|---|
| Moreira & Muir (2017), [*Volatility-Managed Portfolios*](https://doi.org/10.1111/jofi.12513) | 使“按风险状态改变暴露”成为可研究的假设，但不是把波动率开关直接加到已观察两资产数据上的许可。 |
| Cederburg et al. (2020), [*On the performance of volatility-managed portfolios*](https://doi.org/10.1016/j.jfineco.2020.04.015) | 作为同一主题的绩效复核，提醒不能预设波动率管理必然提升结果。因而 v1 不在已看过的历史上追加波动率阈值。 |

## 对策略流程的约束

1. 文献只允许产生不同经济机制的**新假设**；不能用来为已看到的收益曲线挑权重、频率或止损。
2. 两资产 v1 已冻结为 510300/518880、各约 50%、季度首个共同交易日开盘调仓。历史中
   40/60 看起来更好这一事实，不能因上述任何论文而合法化为规则修改。
3. 未来前瞻证据来自 [PAPER_TRACKING_TWO_ASSET_V1.md](PAPER_TRACKING_TWO_ASSET_V1.md) 的连续
   纸面记录；最低观察期为 12 个季度，并与独立的 510300 买入持有基准比较。
4. 论文、历史回测及纸面交易均不构成投资建议、收益承诺或真实资金开仓理由。

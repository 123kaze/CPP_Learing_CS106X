# A 股强势股回调：可证伪研究协议

这个目录是独立研究快照。它服务于一个更严格的目标：寻找**扣费后、样本外可复现的正期望证据**，而不是承诺策略会赚钱。历史回测不是未来收益保证。

## 当前脚本

- `strategy.py`：筛选、ATR 风控、成本与仓位的共用规则。
- `test.py`：每日收盘后的候选生成器。
- `backtest.py`：执行约束、费用、T+1、组合持仓和资金曲线的回测器。

## 已冻结的候选规则

1. 主板股票按当日 60 日涨幅横截面取前 10%。
2. 股票趋势、EMA21 回踩、AVWAP、ATR 止损距离、ATR 封顶目标、整手和成本规则均来自 `strategy.py`。
3. 次日触发才买；高开超过 `max_chase` 不追；一字涨停不假设可买。
4. A 股 T+1：买入日不卖；跳空跌破止损按开盘价；一字跌停延后到可成交日。
5. 新增的唯一大盘假设：信号日收盘时，中证全指（`sh000985`）必须在 EMA50 上方，才在次日挂单。

该市场过滤假设基于风险管理，而非事后把全样本最优参数塞回策略。阈值固定为 EMA50，指数固定为中证全指；不得用 2025 年之后的数据改动它。

## 防数据窥探协议

| 阶段 | 数据 | 允许做什么 | 不允许做什么 |
|---|---|---|---|
| 形成期 | 2022-01-01 至 2024-12-31 | 只比较“无大盘过滤”与“中证全指 > EMA50”这两个预先指定的版本；检查费用、T+1、跌停成交假设是否改变结论 | 搜索 EMA 天数、指数、止损、目标、仓位等多个参数 |
| 锁定 | 形成期结束后 | 选择一个版本并记录命令与文件校验值 | 再根据样本外表现改代码或参数 |
| 样本外 | 2025-01-01 至 2026-06-30 | **只运行一次**锁定版本，报告组合结果与逐信号结果 | 将结果用于反调规则 |

判定不采用单一胜率。至少同时报告：扣费后平均 R、累计净收益、交易笔数、最大回撤、目标命中率、超时/无法平仓次数，以及按年拆分。若样本外平均净 R 不为正、交易笔数太少或回撤超过事先可承受阈值，结论就是“不通过”，而不是继续挖参数。

## 文献依据与边界

1. Moskowitz、Ooi、Pedersen 的 [*Time Series Momentum*](https://doi.org/10.1016/j.jfineco.2011.11.003) 记录了跨资产时间序列动量；它支持把趋势作为可检验假设，不证明任何单一 A 股日线规则获利。
2. Daniel、Moskowitz 的 [*Momentum Crashes*](https://doi.org/10.1016/j.jfineco.2015.12.002) 说明动量在市场快速反弹阶段可能出现严重左尾风险。这是加入市场状态过滤并保守模拟跳空的动机。
3. Barroso、Santa-Clara 的 [*Momentum Has Its Moments*](https://doi.org/10.1016/j.jfineco.2014.11.010) 与 Moreira、Muir 的 [*Volatility-Managed Portfolios*](https://doi.org/10.1111/jofi.12513) 为波动率缩放/风险管理提供跨样本证据；它们不授权把 ATR 参数当作已优化的收益来源。
4. Zhu、Jiang、Li、Zhou 的 [*Profitability of Simple Technical Trading Rules of Chinese Stock Exchange Indexes*](https://doi.org/10.1016/j.physa.2015.08.017) 使用 White Reality Check，指出未计入交易成本时的技术规则结果可能误导。本项目因此把成本、整手、T+1 和不可成交跌停纳入逐笔模拟。
5. Zhang 等的 [*Statistical Properties and Pre-Hit Dynamics of Price Limit Hits in the Chinese Stock Markets*](https://doi.org/10.1371/journal.pone.0120312) 报告跌停事件后的延续风险，这支持将一字跌停视作无法立即按止损价平仓，而非把它当作普通止损成交。

## 已知限制

- 腾讯提供的是当前证券清单：退市股缺失，且以当前名称过滤 ST，会产生存活偏差和 ST 状态的未来信息。
- 日线 OHLC 无法确认盘中止损和目标的先后；代码保守地把同日双触发记为止损。
- 目前不含行业集中度限制；组合资金曲线按最多两只持仓、按止损距离选股模拟，但仍不含真实委托队列和滑点。
- 文献与回测只能构成研究证据，不能构成投资建议或盈利保证。

## 可复现实验命令

```bash
# 形成期：仅比较事先指定的两个版本；分别保存到不同目录
python backtest.py --start 20220101 --end 20241231 --holdout-start none --market-filter none --output-dir results/train_no_filter
python backtest.py --start 20220101 --end 20241231 --holdout-start none --market-filter csi_all_ema50 --output-dir results/train_market_filter

# 锁定后的一次样本外检验（不要根据该结果继续调参）
python backtest.py --start 20250101 --end 20260630 --market-filter csi_all_ema50 --output-dir results/oos_2025_2026
```

# 策略研究实验室

此目录保存可复现的 A 股/境内 ETF 策略研究，不是交易建议，也没有任何通过实盘资格的策略。
截至 2026-10-12，所有已运行候选都被其预先登记的成本后门槛淘汰；详情见
`RESULTS_AUDIT.md`。

## 目录

| 文件 | 用途 | 当前状态 |
|---|---|---|
| `test.py`、`strategy.py`、`backtest.py` | 当前强势股回调候选的完整副本；根目录同名文件与其逐字一致 | 形成期和样本外均不通过 |
| `RESEARCH_PROTOCOL.md` | 个股回调规则、论文依据、分段和防数据窥探约束 | 已执行并记录 |
| `HYPOTHESIS_BREAKOUT_V1.md` / `breakout_backtest.py` | 独立的个股新高突破假设和回测器 | 形成期不通过；未运行其样本外 |
| `HYPOTHESIS_ETF_TREND_V1.md` / `etf_trend_backtest.py` | 510300 单 ETF 趋势开关 | 形成期通过、唯一一次样本外不通过 |
| `HYPOTHESIS_MULTI_ASSET_ETF_V1.md` / `multi_asset_etf_backtest.py` | 股票、国债、黄金 ETF 月度双动量 | 形成期不通过；未运行其样本外 |
| `HYPOTHESIS_EQUAL_WEIGHT_ETF_V1.md` / `equal_weight_etf_backtest.py` | 三资产固定等权 | 2 万元无法满足国债 ETF 整手约束；历史输出已标无效 |
| `HYPOTHESIS_TWO_ASSET_ETF_V1.md` / `two_asset_etf_backtest.py` | 510300/518880 固定等权、季度再平衡 | 冻结为纸面候选；历史后段仅探索性，不可上实盘 |
| `LITERATURE_TWO_ASSET_ETF_V1.md` | 两资产候选的 DOI 核验文献表与反证边界 | 论文解释研究动机，不能取代前瞻验证 |
| `two_asset_raw_total_return_audit.py` | 用未复权成交价和现金分红复算两资产候选 | 与前复权口径方向一致；不改变纸面状态 |
| `two_asset_start_sensitivity_audit.py` | 固定规则的年度起点敏感性审计 | 重叠窗口稳健性描述，不是新的样本外检验 |
| `two_asset_parameter_surface_audit.py` | 预先固定的 3×3 权重/频率完整网格 | 全部报告，专门防止只展示最好参数；不得据此修改纸面规则 |
| `two_asset_raw_parameter_surface_audit.py` | 未复权成交价 + 现金分红下的同一 3×3 网格 | 独立价格口径复算；不得据此修改纸面规则 |
| `ROBUSTNESS_TWO_ASSET_V1.md` / `PAPER_TRACKING_TWO_ASSET_V1.md` / `paper_two_asset_tracker.py` | 两资产候选的成本压力审计、前瞻纸面账本和记录规则 | 独立记录组合与 510300 买入持有基准；跳过季度调仓日即拒绝补录 |
| `paper_two_asset_report.py` | 纸面组合与基准的只读绩效报告 | 汇总实际估值、费用、分红和相对收益；不改账本、不下单 |
| `PAPER_AUTOMATION_TWO_ASSET_V1.md` / `paper_initialize_watchdog.py` | 目标日收盘后的纸面初始化守护 | 已安装为 macOS 用户级任务；仅写虚拟账本，绝不发券商订单 |
| `test_paper_two_asset_tracker.py` / `test_paper_two_asset_report.py` / `test_paper_initialize_watchdog.py` | 纸面账本、报告与时间守护的离线测试 | 不访问网络、不写真实账本 |
| `audit_research_snapshot.py` | 检查脚本副本、结果 JSON 与无效运行标记 | 只读审计 |
| `results/` | 原始 JSON、逐笔交易和资金曲线 CSV | 不修改历史输出 |

## 关键规则

- 先写经济假设、参数、形成期和通过门槛，后运行代码。
- 没通过形成期的策略不查看对应样本外结果；通过者只能进行一次样本外检验。
- 不因结果更换均线、目标、止损、ETF 或时间区间；那是数据窥探，不是策略改进。
- 全部结果必须保留费用、整手、次日成交、T+1 与涨跌停/流动性局限的说明。

## 当前结论

尚无策略满足“可承诺赚钱”的证据标准，因而不能投入真实资金。两资产 ETF 候选可按冻结
规则做纸面跟踪，但不接入 `test.py`。下一候选必须与已有假设在经济机制上独立，并使用
事先保留的验证数据；否则只是在重复试错中挑选历史上看起来最好的一条曲线。

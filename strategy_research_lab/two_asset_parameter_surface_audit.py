"""预先固定网格，审计两资产 ETF 配置的参数敏感性。

这不是用历史收益挑选新规则：权重 {40%, 50%, 60% 沪深 300} 和
再平衡频率 {月、季、年} 在运行前即固定，所有组合均完整报告。成交采用
共同交易日开盘、100 份整手、最低佣金，因此结果仍受小账户可执行性约束。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

import two_asset_etf_backtest as base


WEIGHTS = (0.40, 0.50, 0.60)
FREQUENCIES = {
    "monthly": "M",
    "quarterly": "Q",
    "annual": "Y",
}


def schedule_days(panel: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp,
                  frequency: str) -> set[pd.Timestamp]:
    """首日建仓，之后按每个自然周期的第一个共同交易日调仓。"""
    data = panel[(panel["date"] >= start) & (panel["date"] <= end)]
    starts = data.groupby(data["date"].dt.to_period(FREQUENCIES[frequency]), sort=False).head(1)
    return set(starts["date"])


def simulate(panel: pd.DataFrame, cfg: Any, stock_weight: float,
             frequency: str) -> dict[str, Any]:
    data = panel[(panel["date"] >= cfg.start) & (panel["date"] <= cfg.end)].reset_index(drop=True)
    if len(data) < 2:
        raise RuntimeError("回测区间没有足够共同交易日")

    target_weights = {"510300": stock_weight, "518880": 1.0 - stock_weight}
    first = data.iloc[0]
    impossible = [
        code for code, weight in target_weights.items()
        if cfg.account * weight < 100 * float(first[f"open_{code}"])
    ]
    if impossible:
        return {
            "stock_weight": stock_weight,
            "frequency": frequency,
            "status": "infeasible_initial_lot",
            "reason": f"初始目标仓位不足一手：{','.join(impossible)}",
        }

    cash = float(cfg.account)
    shares = {code: 0 for code in base.ASSETS}
    scheduled = schedule_days(panel, cfg.start, cfg.end, frequency)
    commissions: list[float] = []
    equity_values: list[float] = []
    trades = 0

    for _, row in data.iterrows():
        day = row["date"]
        if day in scheduled:
            nav = cash + sum(shares[code] * float(row[f"open_{code}"])
                             for code in base.ASSETS)
            desired = {
                code: int(nav * target_weights[code] / float(row[f"open_{code}"]) // 100 * 100)
                for code in base.ASSETS
            }
            # 卖出先于买入，避免把未来卖出所得用于当前开盘买入。
            for code in base.ASSETS:
                excess = max(0, shares[code] - desired[code])
                if excess >= 100:
                    price = base.execution_price(float(row[f"open_{code}"]), "sell", cfg)
                    fee = base.commission(excess * price, cfg)
                    cash += excess * price - fee
                    shares[code] -= excess
                    commissions.append(fee)
                    trades += 1
            for code in base.ASSETS:
                deficit = max(0, desired[code] - shares[code])
                if deficit >= 100:
                    price = base.execution_price(float(row[f"open_{code}"]), "buy", cfg)
                    quantity, fee = base.buy_limited(cash, deficit, price, cfg)
                    if quantity:
                        cash -= quantity * price + fee
                        shares[code] += quantity
                        commissions.append(fee)
                        trades += 1
        equity_values.append(cash + sum(shares[code] * float(row[f"close_{code}"])
                                        for code in base.ASSETS))

    equity = pd.Series(equity_values, dtype=float)
    terminal = float(equity.iloc[-1])
    years = (data.iloc[-1]["date"] - data.iloc[0]["date"]).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 else None
    drawdown = equity / equity.cummax() - 1
    return {
        "stock_weight": stock_weight,
        "frequency": frequency,
        "status": "ok",
        "terminal_equity": round(terminal, 2),
        "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "scheduled_rebalances": len(scheduled),
        "actual_trades": trades,
        "total_commission": round(sum(commissions), 2),
        "end_cash": round(cash, 2),
        "end_shares": shares,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="两资产 ETF 固定参数网格审计（非参数选择）")
    parser.add_argument("--start", required=True, type=lambda value: pd.Timestamp(value).normalize())
    parser.add_argument("--end", required=True, type=lambda value: pd.Timestamp(value).normalize())
    parser.add_argument("--account", type=float, default=20_000)
    parser.add_argument("--fee-rate", type=float, default=0.00025)
    parser.add_argument("--min-fee", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--cache-dir", type=Path, default=Path("../backtest_cache/tencent_daily"))
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    cfg = parser.parse_args()
    if (not cfg.start < cfg.end or cfg.account <= 0 or cfg.fee_rate < 0 or cfg.min_fee < 0
            or cfg.slippage_bps < 0 or cfg.slippage_bps >= 10_000):
        parser.error("时间、账户、费用或滑点参数无效")
    return cfg


def main() -> None:
    cfg = parse_args()
    # base.load_panel 只依赖以下字段；独立构造避免把新网格参数混入核心策略的接口。
    load_cfg = SimpleNamespace(end=cfg.end, cache_dir=cfg.cache_dir, refresh=cfg.refresh)
    panel = base.load_panel(load_cfg)
    rows = [simulate(panel, cfg, weight, frequency)
            for frequency in FREQUENCIES for weight in WEIGHTS]
    table = pd.DataFrame(rows)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(cfg.output_dir / f"surface_{stem}.csv", index=False, encoding="utf-8-sig")
    summary = {
        "hypothesis": "two_asset_etf_fixed_grid_robustness_audit",
        "data_adjustment": "qfq; 近似分红再投资",
        "predeclared_grid": {
            "weight_510300": list(WEIGHTS),
            "weight_518880": [round(1.0 - weight, 2) for weight in WEIGHTS],
            "rebalance_frequency": list(FREQUENCIES),
        },
        "assumptions": {key: (str(value) if isinstance(value, (Path, pd.Timestamp)) else value)
                        for key, value in vars(cfg).items()},
        "results": rows,
        "interpretation": [
            "本表完整披露预先固定的 3×3 网格，不能按最高收益单元事后改写纸面策略。",
            "历史正收益不代表未来盈利；纸面交易规则仍固定为 50/50、季度再平衡。",
            "结果未模拟盘口冲击、跟踪误差、申赎与停牌。",
        ],
    }
    (cfg.output_dir / f"summary_{stem}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("===== 两资产 ETF 固定网格稳健性审计 =====")
    print(table[["frequency", "stock_weight", "status", "cagr_pct", "max_drawdown_pct",
                 "actual_trades", "total_commission"]].to_string(index=False))
    print(f"输出目录：{cfg.output_dir}")


if __name__ == "__main__":
    main()

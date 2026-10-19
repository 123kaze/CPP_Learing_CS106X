"""研究候选五：预登记的股、债、黄金 ETF 固定等权季度再平衡。

规则见 HYPOTHESIS_EQUAL_WEIGHT_ETF_V1.md。使用腾讯前复权日线和实际账户的整手、
最低佣金、现金约束；仅供研究，不构成投资建议。
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from multi_asset_etf_backtest import ASSETS, BENCHMARK, benchmark, commission, load_panel


@dataclass
class Holding:
    shares: int = 0
    cost_basis: float = 0.0


def _buy_limited(cash: float, desired: int, price: float, cfg) -> tuple[int, float]:
    """在目标份额和实际现金内买入，不让某一标的耗尽其他标的的预算。"""
    shares = desired // 100 * 100
    while shares >= 100:
        amount = shares * price
        fee = commission(amount, cfg)
        if amount + fee <= cash + 1e-9:
            return shares, fee
        shares -= 100
    return 0, 0.0


def rebalance_dates(panel: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> set[pd.Timestamp]:
    window = panel[(panel["date"] >= start) & (panel["date"] <= end)]
    return set(window.groupby(window["date"].dt.to_period("Q"), sort=False).head(1)["date"])


def validate_initial_lot_feasibility(panel: pd.DataFrame, cfg) -> None:
    """不能把“买不起一手”悄悄变成现金仓位，否则会改变预登记的等权策略。"""
    first = panel[panel["date"] >= cfg.start].iloc[0]
    target_value = cfg.account / len(ASSETS)
    infeasible = []
    for code in ASSETS:
        lot_cost = 100 * float(first[f"open_{code}"])
        if target_value < lot_cost:
            infeasible.append(f"{code} 一手约 {lot_cost:.2f} 元，目标仓位仅 {target_value:.2f} 元")
    if infeasible:
        raise RuntimeError(
            "账户资金不足以按预登记规则为每只 ETF 买入一手；不能把缺口当现金而继续回测："
            + "；".join(infeasible)
        )


def simulate(panel: pd.DataFrame, cfg) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    window = panel[(panel["date"] >= cfg.start) & (panel["date"] <= cfg.end)].reset_index(drop=True)
    if len(window) < 2:
        raise RuntimeError("回测区间没有足够共同交易日")
    dates = rebalance_dates(panel, cfg.start, cfg.end)
    cash = float(cfg.account)
    holdings = {code: Holding() for code in ASSETS}
    events: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    rebalance_count = 0

    for _, row in window.iterrows():
        day = row.date
        if day in dates:
            # 使用今天开盘价计算调仓前净值；调仓没有信息优势，因为日期是日历规则。
            nav = cash + sum(holdings[code].shares * float(row[f"open_{code}"]) for code in ASSETS)
            target_value = nav / len(ASSETS)
            desired = {code: int(target_value / float(row[f"open_{code}"]) // 100 * 100) for code in ASSETS}

            # 先全部处理超配卖出，让补仓不会受人为顺序的现金不足影响。
            for code in ASSETS:
                held = holdings[code]
                excess = max(0, held.shares - desired[code])
                if excess < 100:
                    continue
                price = float(row[f"open_{code}"])
                amount = excess * price
                fee = commission(amount, cfg)
                cash += amount - fee
                old_shares = held.shares
                held.shares -= excess
                if held.shares == 0:
                    held.cost_basis = 0.0
                events.append({"date": day.date(), "side": "sell", "code": code,
                               "price": round(price, 4), "shares": excess,
                               "commission": round(fee, 2), "cash_after": round(cash, 2),
                               "shares_before": old_shares, "shares_after": held.shares})

            # 再按固定代码次序补仓；每次只能买到本标的预定的整手数量。
            for code in ASSETS:
                held = holdings[code]
                deficit = max(0, desired[code] - held.shares)
                if deficit < 100:
                    continue
                price = float(row[f"open_{code}"])
                shares, fee = _buy_limited(cash, deficit, price, cfg)
                if not shares:
                    continue
                amount = shares * price
                old_shares = held.shares
                old_cost = held.cost_basis * old_shares
                cash -= amount + fee
                held.shares += shares
                held.cost_basis = (old_cost + amount + fee) / held.shares
                events.append({"date": day.date(), "side": "buy", "code": code,
                               "price": round(price, 4), "shares": shares,
                               "commission": round(fee, 2), "cash_after": round(cash, 2),
                               "shares_before": old_shares, "shares_after": held.shares})
            rebalance_count += 1

        equity = cash + sum(holdings[code].shares * float(row[f"close_{code}"]) for code in ASSETS)
        equity_rows.append({"date": day.date(), "equity": round(equity, 2), "cash": round(cash, 2),
                            **{f"shares_{code}": holdings[code].shares for code in ASSETS}})

    trades = pd.DataFrame(events)
    curve = pd.DataFrame(equity_rows)
    terminal = float(curve.iloc[-1].equity)
    years = (pd.Timestamp(curve.iloc[-1].date) - pd.Timestamp(curve.iloc[0].date)).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 else None
    drawdown = curve["equity"] / curve["equity"].cummax() - 1
    return trades, curve, {
        "start_date": str(curve.iloc[0].date),
        "end_date": str(curve.iloc[-1].date),
        "terminal_equity": round(terminal, 2),
        "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "scheduled_rebalances": rebalance_count,
        "actual_trades": int(len(trades)),
        "actual_buys": int((trades["side"] == "buy").sum()) if not trades.empty else 0,
        "total_commission": round(float(trades["commission"].sum()), 2) if not trades.empty else 0.0,
        "end_shares": {code: holdings[code].shares for code in ASSETS},
        "end_cash": round(cash, 2),
    }


def gate(strategy: dict[str, Any], passive: dict[str, Any], cfg) -> dict[str, Any]:
    if cfg.end.year <= 2020:
        rule = "年化收益 > 0、至少 20 次实际买入、最大回撤不差于 510300 买入持有"
        passed = (strategy["cagr_pct"] is not None and strategy["cagr_pct"] > 0
                  and strategy["actual_buys"] >= 20
                  and strategy["max_drawdown_pct"] >= passive["max_drawdown_pct"])
    else:
        rule = "年化收益 > 0、期末净资产高于初始资金、最大回撤不差于 510300 买入持有"
        passed = (strategy["cagr_pct"] is not None and strategy["cagr_pct"] > 0
                  and strategy["terminal_equity"] > cfg.account
                  and strategy["max_drawdown_pct"] >= passive["max_drawdown_pct"])
    return {"rule": rule, "passed": bool(passed)}


def parse_args():
    parser = argparse.ArgumentParser(description="股债黄金 ETF 固定等权季度再平衡回测")
    parser.add_argument("--start", type=lambda x: pd.Timestamp(x).normalize(), required=True)
    parser.add_argument("--end", type=lambda x: pd.Timestamp(x).normalize(), required=True)
    parser.add_argument("--account", type=float, default=20_000)
    parser.add_argument("--fee-rate", type=float, default=0.00025)
    parser.add_argument("--min-fee", type=float, default=5.0)
    parser.add_argument("--cache-dir", type=Path, default=Path("../backtest_cache/tencent_daily"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true")
    cfg = parser.parse_args()
    if not cfg.start < cfg.end:
        parser.error("--start 必须早于 --end")
    if cfg.account <= 0 or cfg.fee_rate < 0 or cfg.min_fee < 0:
        parser.error("账户或费用参数无效")
    return cfg


def main() -> None:
    cfg = parse_args()
    panel = load_panel(cfg)
    validate_initial_lot_feasibility(panel, cfg)
    trades, equity, strategy = simulate(panel, cfg)
    passive = benchmark(panel, cfg)
    result = {
        "hypothesis": "equal_weight_etf_v1",
        "assets": ASSETS,
        "data_adjustment": "qfq",
        "assumptions": {key: (str(value) if isinstance(value, (Path, pd.Timestamp)) else value)
                        for key, value in vars(cfg).items()},
        "strategy": strategy,
        "buy_and_hold_510300_reference": passive,
        "gate": gate(strategy, passive, cfg),
        "caveats": ["前复权价格近似分红再投资", "未模拟盘口滑点、ETF 跟踪误差、申赎或停牌",
                    "实际券商费用变化时必须重跑"],
    }
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    trades.to_csv(cfg.output_dir / f"trades_{stem}.csv", index=False, encoding="utf-8-sig")
    equity.to_csv(cfg.output_dir / f"equity_{stem}.csv", index=False, encoding="utf-8-sig")
    (cfg.output_dir / f"summary_{stem}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("===== 固定等权 ETF 配置 =====")
    print(f"策略：期末 {strategy['terminal_equity']} 元，收益 {strategy['total_return_pct']}%，"
          f"年化 {strategy['cagr_pct']}%，最大回撤 {strategy['max_drawdown_pct']}%，"
          f"买入 {strategy['actual_buys']} 次，佣金 {strategy['total_commission']} 元")
    print(f"510300 买入持有：期末 {passive['terminal_equity']} 元，收益 {passive['total_return_pct']}%，"
          f"年化 {passive['cagr_pct']}%，最大回撤 {passive['max_drawdown_pct']}%")
    print("形成/样本外门槛：" + ("通过" if result["gate"]["passed"] else "不通过"))
    print(f"输出目录：{cfg.output_dir}")


if __name__ == "__main__":
    main()

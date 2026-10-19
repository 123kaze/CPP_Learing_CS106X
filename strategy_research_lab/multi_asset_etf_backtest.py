"""研究候选四：预先登记的境内股、债、黄金 ETF 月度双动量。

参见 HYPOTHESIS_MULTI_ASSET_ETF_V1.md。所有调仓都滞后一个共同交易日开盘执行，且以
100 份、最低佣金和现金约束计算；这不是实盘交易程序或投资建议。
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

import backtest as B


ASSETS = {
    "510300": "sh510300",  # 股票
    "511010": "sh511010",  # 国债
    "518880": "sh518880",  # 黄金
}
BENCHMARK = "510300"


@dataclass
class Holding:
    code: str
    shares: int
    entry_date: pd.Timestamp
    entry_price: float
    buy_cost: float


def commission(amount: float, cfg) -> float:
    return max(cfg.min_fee, amount * cfg.fee_rate)


def buy_shares(cash: float, price: float, cfg) -> tuple[int, float]:
    shares = int(cash / (price * (1 + cfg.fee_rate)) // 100 * 100)
    while shares >= 100:
        amount = shares * price
        fee = commission(amount, cfg)
        if amount + fee <= cash + 1e-9:
            return shares, fee
        shares -= 100
    return 0, 0.0


def load_panel(cfg) -> pd.DataFrame:
    series: list[pd.DataFrame] = []
    for code, symbol in ASSETS.items():
        history = B.load_history(code, pd.Timestamp("20130101"), cfg.end,
                                 cfg.cache_dir, cfg.refresh, symbol)
        if history is None or len(history) < 264:
            raise RuntimeError(f"无法取得 {code} 的足够长腾讯日线")
        part = history[["date", "open", "close"]].rename(
            columns={"open": f"open_{code}", "close": f"close_{code}"})
        series.append(part)
    panel = series[0]
    for part in series[1:]:
        panel = panel.merge(part, on="date", how="inner")
    panel = panel.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    for code in ASSETS:
        panel[f"return_{code}"] = panel[f"close_{code}"].pct_change(252)
    return panel


def signal_days(panel: pd.DataFrame) -> set[pd.Timestamp]:
    months = panel["date"].dt.to_period("M")
    return set(panel.groupby(months, sort=False).tail(1)["date"])


def benchmark(panel: pd.DataFrame, cfg) -> dict[str, Any]:
    window = panel[(panel["date"] >= cfg.start) & (panel["date"] <= cfg.end)].reset_index(drop=True)
    if len(window) < 2:
        raise RuntimeError("基准区间没有足够日线")
    entry = float(window.iloc[0][f"open_{BENCHMARK}"])
    shares, fee = buy_shares(cfg.account, entry, cfg)
    cash = cfg.account - shares * entry - fee
    equity = cash + shares * window[f"close_{BENCHMARK}"]
    drawdown = equity / equity.cummax() - 1
    terminal = float(equity.iloc[-1])
    years = (window.iloc[-1].date - window.iloc[0].date).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 else None
    return {
        "symbol": BENCHMARK,
        "terminal_equity": round(terminal, 2),
        "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "entry_cost": round(fee, 2),
    }


def simulate(panel: pd.DataFrame, cfg) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    start_indices = panel.index[panel["date"] >= cfg.start]
    end_indices = panel.index[panel["date"] <= cfg.end]
    if not len(start_indices) or not len(end_indices):
        raise RuntimeError("回测区间不在 ETF 日线范围内")
    first, last = int(start_indices[0]), int(end_indices[-1])
    sig_days = signal_days(panel)
    cash = float(cfg.account)
    holding: Holding | None = None
    pending: str | None | object = _NO_SIGNAL  # 首日没有前一日信号，不进行交易。
    events: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    selection_counts = {"cash": 0, **{code: 0 for code in ASSETS}}

    for i in range(first, last + 1):
        row = panel.iloc[i]
        day = row.date
        # `pending_target` 独立存放，避免把 None（现金）和“尚无信号”混在一起。
        # 这个属性只在循环局部使用，首日为 False 表示不执行。
        if i == first:
            execute = False
            target: str | None = None
        else:
            execute = pending is not _NO_SIGNAL
            target = pending if execute else None
        if execute and target != (holding.code if holding else None):
            if holding is not None:
                sell_price = float(row[f"open_{holding.code}"])
                amount = holding.shares * sell_price
                fee = commission(amount, cfg)
                cash += amount - fee
                events.append({
                    "date": day.date(), "side": "sell", "code": holding.code,
                    "price": round(sell_price, 4), "shares": holding.shares,
                    "commission": round(fee, 2), "cash_after": round(cash, 2),
                    "entry_date": holding.entry_date.date(), "entry_price": round(holding.entry_price, 4),
                    "net_pnl": round(holding.shares * (sell_price - holding.entry_price) - holding.buy_cost - fee, 2),
                })
                holding = None
            if target is not None:
                buy_price = float(row[f"open_{target}"])
                shares, fee = buy_shares(cash, buy_price, cfg)
                if shares:
                    cash -= shares * buy_price + fee
                    holding = Holding(target, shares, day, buy_price, fee)
                    events.append({
                        "date": day.date(), "side": "buy", "code": target,
                        "price": round(buy_price, 4), "shares": shares,
                        "commission": round(fee, 2), "cash_after": round(cash, 2),
                    })

        close_equity = cash if holding is None else cash + holding.shares * float(row[f"close_{holding.code}"])
        equity_rows.append({"date": day.date(), "equity": round(close_equity, 2),
                            "holding": holding.code if holding else "cash"})

        if day in sig_days and i < last:
            returns = {code: row[f"return_{code}"] for code in ASSETS}
            if all(pd.notna(value) for value in returns.values()):
                best = max(returns, key=returns.get)
                pending = best if returns[best] > 0 else None
                selection_counts[pending or "cash"] += 1
            else:
                pending = _NO_SIGNAL
        else:
            pending = _NO_SIGNAL

    trades = pd.DataFrame(events)
    equity = pd.DataFrame(equity_rows)
    sells = trades[trades["side"] == "sell"].copy() if not trades.empty else pd.DataFrame()
    terminal = float(equity.iloc[-1].equity)
    years = (pd.Timestamp(equity.iloc[-1].date) - pd.Timestamp(equity.iloc[0].date)).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 else None
    drawdown = equity["equity"] / equity["equity"].cummax() - 1
    summary = {
        "start_date": str(equity.iloc[0].date),
        "end_date": str(equity.iloc[-1].date),
        "terminal_equity": round(terminal, 2),
        "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "actual_switches": int((trades["side"] == "buy").sum()) if not trades.empty else 0,
        "complete_round_trips": int(len(sells)),
        "total_commission": round(float(trades["commission"].sum()), 2) if not trades.empty else 0.0,
        "closed_win_rate_pct": round(float((sells["net_pnl"] > 0).mean()) * 100, 2) if not sells.empty else None,
        "signal_selection_counts": selection_counts,
        "open_holding_at_end": holding.code if holding else None,
    }
    return trades, equity, summary


# Sentinel needs a distinct identity; `None` is a valid cash target.
_NO_SIGNAL = object()


def gate(strategy: dict[str, Any], passive: dict[str, Any], cfg) -> dict[str, Any]:
    if cfg.end.year <= 2020:
        rule = "年化收益 > 0、至少 12 次实际换仓、最大回撤不差于 510300 买入持有"
        passed = (strategy["cagr_pct"] is not None and strategy["cagr_pct"] > 0
                  and strategy["actual_switches"] >= 12
                  and strategy["max_drawdown_pct"] >= passive["max_drawdown_pct"])
    else:
        rule = "年化收益 > 0、期末净资产高于初始资金、最大回撤不差于 510300 买入持有"
        passed = (strategy["cagr_pct"] is not None and strategy["cagr_pct"] > 0
                  and strategy["terminal_equity"] > cfg.account
                  and strategy["max_drawdown_pct"] >= passive["max_drawdown_pct"])
    return {"rule": rule, "passed": bool(passed)}


def parse_args():
    parser = argparse.ArgumentParser(description="预登记的境内多资产 ETF 月度双动量回测")
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
    trades, equity, strategy = simulate(panel, cfg)
    passive = benchmark(panel, cfg)
    result = {
        "hypothesis": "multi_asset_etf_v1",
        "assets": ASSETS,
        "data_adjustment": "qfq",
        "assumptions": {key: (str(value) if isinstance(value, (Path, pd.Timestamp)) else value)
                        for key, value in vars(cfg).items()},
        "strategy": strategy,
        "buy_and_hold_510300_reference": passive,
        "gate": gate(strategy, passive, cfg),
        "caveats": ["前复权价格近似分红再投资", "未模拟盘口滑点、申赎、ETF 跟踪误差或基金停牌",
                    "实际券商费用不同必须重跑"],
    }
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    trades.to_csv(cfg.output_dir / f"trades_{stem}.csv", index=False, encoding="utf-8-sig")
    equity.to_csv(cfg.output_dir / f"equity_{stem}.csv", index=False, encoding="utf-8-sig")
    (cfg.output_dir / f"summary_{stem}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("===== 多资产 ETF 月度双动量 =====")
    print(f"策略：期末 {strategy['terminal_equity']} 元，收益 {strategy['total_return_pct']}%，"
          f"年化 {strategy['cagr_pct']}%，最大回撤 {strategy['max_drawdown_pct']}%，"
          f"实际换仓 {strategy['actual_switches']} 次，佣金 {strategy['total_commission']} 元")
    print(f"510300 买入持有：期末 {passive['terminal_equity']} 元，收益 {passive['total_return_pct']}%，"
          f"年化 {passive['cagr_pct']}%，最大回撤 {passive['max_drawdown_pct']}%")
    print("形成/样本外门槛：" + ("通过" if result["gate"]["passed"] else "不通过"))
    print(f"输出目录：{cfg.output_dir}")


if __name__ == "__main__":
    main()

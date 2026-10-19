"""研究候选三：510300 的中长期趋势开关（仅研究，不构成投资建议）。

规则、固定参数和形成期/样本外门槛见 HYPOTHESIS_ETF_TREND_V1.md。使用腾讯前复权日线；
成交始终滞后一日，以避免用收盘信号按收盘价成交的前视偏差。
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

import backtest as B


ETF_CODE = "510300"
ETF_SYMBOL = "sh510300"


@dataclass
class Position:
    shares: int
    entry_date: pd.Timestamp
    entry_price: float
    buy_cost: float


def commission(amount: float, cfg) -> float:
    return max(cfg.min_fee, amount * cfg.fee_rate)


def add_indicators(history: pd.DataFrame) -> pd.DataFrame:
    f = history.copy().reset_index(drop=True)
    f["sma200"] = f["close"].rolling(200).mean()
    f["return63"] = f["close"].pct_change(63)
    f["desired_exposure"] = (f["close"] > f["sma200"]) & (f["return63"] > 0)
    return f


def buy_shares(cash: float, price: float, cfg) -> tuple[int, float]:
    """按 100 份整数手和最低佣金反推最多可买的份额。"""
    guess = int(cash / (price * (1 + cfg.fee_rate)) // 100 * 100)
    while guess >= 100:
        amount = guess * price
        fee = commission(amount, cfg)
        if amount + fee <= cash + 1e-9:
            return guess, fee
        guess -= 100
    return 0, 0.0


def buy_and_hold(history: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, cfg) -> dict[str, Any]:
    """同一日期、同一费用起点下的被动持有对照；期末按收盘价标记。"""
    window = history[(history["date"] >= start) & (history["date"] <= end)].reset_index(drop=True)
    if len(window) < 2:
        raise RuntimeError("对照区间没有足够 ETF 日线")
    entry = float(window.iloc[0].open)
    shares, fee = buy_shares(cfg.account, entry, cfg)
    cash = cfg.account - shares * entry - fee
    equity = cash + shares * window["close"]
    max_dd = float((equity / equity.cummax() - 1).min())
    terminal = float(equity.iloc[-1])
    years = (window.iloc[-1].date - window.iloc[0].date).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 and terminal > 0 else None
    return {
        "start_date": str(window.iloc[0].date.date()),
        "entry_price": round(entry, 4),
        "shares": shares,
        "cost": round(fee, 2),
        "terminal_equity": round(terminal, 2),
        "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
        "cagr_pct": None if cagr is None else round(cagr * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
    }


def simulate(history: pd.DataFrame, cfg) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """按 t 日收盘信号，在 t+1 开盘切换。最后一天仅期末标记而不创建虚构平仓。"""
    f = add_indicators(history)
    f = f[(f["date"] >= cfg.start) & (f["date"] <= cfg.end)].copy().reset_index(drop=True)
    # 用完整历史计算指标后再切片，避免在研究区间开始点重新预热。
    full = add_indicators(history)
    start_idx = int(full.index[full["date"] >= cfg.start][0])
    end_idx = int(full.index[full["date"] <= cfg.end][-1])
    if end_idx - start_idx < 2:
        raise RuntimeError("回测区间没有足够 ETF 日线")

    cash = float(cfg.account)
    position: Position | None = None
    ledger: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    pending: bool | None = None

    for i in range(start_idx, end_idx + 1):
        row = full.iloc[i]
        day = row.date
        # 昨天收盘后的状态，在今天开盘执行。没有足够指标的第一天不交易。
        if pending is not None:
            open_price = float(row.open)
            if pending and position is None:
                shares, fee = buy_shares(cash, open_price, cfg)
                if shares:
                    cash -= shares * open_price + fee
                    position = Position(shares, day, open_price, fee)
                    ledger.append({
                        "date": day.date(), "side": "buy", "price": round(open_price, 4),
                        "shares": shares, "commission": round(fee, 2), "cash_after": round(cash, 2),
                    })
            elif not pending and position is not None:
                amount = position.shares * open_price
                fee = commission(amount, cfg)
                proceeds = amount - fee  # ETF 卖出印花税固定为 0，见预登记假设。
                cash += proceeds
                gross = position.shares * (open_price - position.entry_price)
                net = gross - position.buy_cost - fee
                ledger.append({
                    "date": day.date(), "side": "sell", "price": round(open_price, 4),
                    "shares": position.shares, "commission": round(fee, 2), "cash_after": round(cash, 2),
                    "entry_date": position.entry_date.date(), "entry_price": round(position.entry_price, 4),
                    "gross_pnl": round(gross, 2), "net_pnl": round(net, 2),
                })
                position = None

        close_equity = cash if position is None else cash + position.shares * float(row.close)
        equity_rows.append({"date": day.date(), "equity": round(close_equity, 2), "in_market": position is not None})
        # 信号只在收盘后生成；最后一个数据日后没有下一日开盘，因此不排队。
        if i < end_idx and pd.notna(row.sma200) and pd.notna(row.return63):
            pending = bool(row.desired_exposure)

    trades = pd.DataFrame(ledger)
    equity = pd.DataFrame(equity_rows)
    closed = trades[trades["side"] == "sell"].copy() if not trades.empty else pd.DataFrame()
    terminal = float(equity.iloc[-1].equity)
    years = (pd.Timestamp(equity.iloc[-1].date) - pd.Timestamp(equity.iloc[0].date)).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 and terminal > 0 else None
    drawdown = equity["equity"] / equity["equity"].cummax() - 1
    summary = {
        "start_date": str(equity.iloc[0].date),
        "end_date": str(equity.iloc[-1].date),
        "complete_round_trips": int(len(closed)),
        "entry_count": int((trades["side"] == "buy").sum()) if not trades.empty else 0,
        "terminal_equity": round(terminal, 2),
        "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
        "cagr_pct": None if cagr is None else round(cagr * 100, 2),
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "total_commission": round(float(trades["commission"].sum()), 2) if not trades.empty else 0.0,
        "closed_win_rate_pct": (round(float((closed["net_pnl"] > 0).mean()) * 100, 2)
                                if not closed.empty else None),
        "closed_total_net_pnl": (round(float(closed["net_pnl"].sum()), 2)
                                  if not closed.empty else 0.0),
        "open_position_at_end": position is not None,
    }
    return trades, equity, summary


def formation_gate(strategy: dict[str, Any], passive: dict[str, Any]) -> dict[str, Any]:
    passed = (strategy["cagr_pct"] is not None and strategy["cagr_pct"] > 0
              and strategy["complete_round_trips"] >= 5
              and strategy["max_drawdown_pct"] >= passive["max_drawdown_pct"])
    return {
        "rule": "年化收益 > 0、至少 5 次完整往返、最大回撤不差于买入持有",
        "passed": bool(passed),
    }


def oos_gate(strategy: dict[str, Any], passive: dict[str, Any], account: float) -> dict[str, Any]:
    passed = (strategy["cagr_pct"] is not None and strategy["cagr_pct"] > 0
              and strategy["terminal_equity"] > account
              and strategy["max_drawdown_pct"] >= passive["max_drawdown_pct"])
    return {
        "rule": "年化收益 > 0、期末净资产高于初始资金、最大回撤不差于买入持有",
        "passed": bool(passed),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="510300 的预登记趋势开关回测")
    parser.add_argument("--start", type=lambda x: pd.Timestamp(x).normalize(), required=True)
    parser.add_argument("--end", type=lambda x: pd.Timestamp(x).normalize(), required=True)
    parser.add_argument("--account", type=float, default=20_000)
    parser.add_argument("--fee-rate", type=float, default=0.00025)
    parser.add_argument("--min-fee", type=float, default=5.0)
    parser.add_argument("--cache-dir", type=Path, default=Path("../backtest_cache/tencent_daily"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true")
    cfg = parser.parse_args()
    if not (cfg.start < cfg.end):
        parser.error("--start 必须早于 --end")
    if cfg.account <= 0 or cfg.fee_rate < 0 or cfg.min_fee < 0:
        parser.error("账户和费用参数无效")
    return cfg


def main() -> None:
    cfg = parse_args()
    # 510300 的腾讯历史从 2012 年开始；不要求更早的虚构数据。
    history = B.load_history(ETF_CODE, pd.Timestamp("20120101"), cfg.end,
                             cfg.cache_dir, cfg.refresh, ETF_SYMBOL)
    if history is None or len(history) < 264:
        raise RuntimeError("无法取得 510300 的足够长腾讯日线")
    trades, equity, strategy = simulate(history, cfg)
    passive = buy_and_hold(history, cfg.start, cfg.end, cfg)
    gate = (formation_gate(strategy, passive) if cfg.end.year <= 2020
            else oos_gate(strategy, passive, cfg.account))
    result = {
        "hypothesis": "etf_trend_v1",
        "symbol": ETF_SYMBOL,
        "data_adjustment": "qfq",
        "assumptions": {key: (str(value) if isinstance(value, (Path, pd.Timestamp)) else value)
                        for key, value in vars(cfg).items()},
        "strategy": strategy,
        "buy_and_hold_reference": passive,
        "gate": gate,
        "caveats": ["前复权价格近似含分红再投资；实际分红到账和再投资时点可能不同",
                    "未模拟盘口滑点、ETF 跟踪误差和暂停申赎", "实际券商佣金不同必须重跑"],
    }
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    trades.to_csv(cfg.output_dir / f"trades_{stem}.csv", index=False, encoding="utf-8-sig")
    equity.to_csv(cfg.output_dir / f"equity_{stem}.csv", index=False, encoding="utf-8-sig")
    (cfg.output_dir / f"summary_{stem}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("===== 510300 趋势开关 =====")
    print(f"策略：期末 {strategy['terminal_equity']} 元，收益 {strategy['total_return_pct']}%，"
          f"年化 {strategy['cagr_pct']}%，最大回撤 {strategy['max_drawdown_pct']}%，"
          f"完整往返 {strategy['complete_round_trips']} 次，佣金 {strategy['total_commission']} 元")
    print(f"买入持有：期末 {passive['terminal_equity']} 元，收益 {passive['total_return_pct']}%，"
          f"年化 {passive['cagr_pct']}%，最大回撤 {passive['max_drawdown_pct']}%")
    print("形成/样本外门槛：" + ("通过" if gate["passed"] else "不通过"))
    print(f"输出目录：{cfg.output_dir}")


if __name__ == "__main__":
    main()

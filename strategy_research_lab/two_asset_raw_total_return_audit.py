"""用未复权 ETF 价格和现金分红复算两资产 ETF 配置。

这是对 two_asset_etf_backtest.py 前复权总回报近似的独立实现审计，不是新策略或参数搜索。
交易按原始开盘价、100 份整手、最低佣金；分红按新浪累计分红的增量进入现金并在季度再平衡
时可以被再投入。默认参数保持冻结的 50/50 季度再平衡；内部函数也供固定网格审计复用。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import time
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd

import backtest as B


ASSETS = {"510300": "sh510300", "518880": "sh518880"}
FREQUENCIES = {"monthly": "M", "quarterly": "Q", "annual": "Y"}


def raw_history(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                raw = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start.strftime("%Y%m%d"),
                                             end_date=end.strftime("%Y%m%d"), adjust="", timeout=20)
            data = B.normalize_history(raw)
            if data is None:
                raise RuntimeError("空或无效日线")
            return data
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"无法取得 {symbol} 未复权日线：{last_error}")


def load_panel(cfg) -> pd.DataFrame:
    panel: pd.DataFrame | None = None
    for code, symbol in ASSETS.items():
        history = raw_history(symbol, pd.Timestamp("20130101"), cfg.end)
        part = history[["date", "open", "close", "volume"]].rename(
            columns={"open": f"open_{code}", "close": f"close_{code}", "volume": f"volume_{code}"})
        panel = part if panel is None else panel.merge(part, on="date", how="inner")
    assert panel is not None
    panel = panel.sort_values("date").reset_index(drop=True)
    invalid = [code for code in ASSETS if (panel[f"volume_{code}"] <= 0).any()]
    if invalid:
        raise RuntimeError(f"共同交易日存在零/负成交量，不能假设可成交：{','.join(invalid)}")
    return panel


def dividend_schedule(end: pd.Timestamp) -> dict[pd.Timestamp, dict[str, float]]:
    """返回 date -> {code: 每份现金分红}；518880 无记录时自然为空。"""
    schedule: dict[pd.Timestamp, dict[str, float]] = {}
    for code, symbol in ASSETS.items():
        with contextlib.redirect_stderr(io.StringIO()):
            table = ak.fund_etf_dividend_sina(symbol=symbol)
        if table is None or table.empty:
            continue
        data = table.rename(columns={"日期": "date", "累计分红": "cumulative"})[["date", "cumulative"]].copy()
        data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
        data["cumulative"] = pd.to_numeric(data["cumulative"], errors="coerce")
        data = data.dropna().sort_values("date")
        data["per_share"] = data["cumulative"].diff().fillna(0.0)
        for row in data.itertuples(index=False):
            if row.date <= end and row.per_share > 0:
                schedule.setdefault(row.date, {})[code] = float(row.per_share)
    return schedule


def commission(amount: float, cfg) -> float:
    return max(cfg.min_fee, amount * cfg.fee_rate)


def buy_limited(cash: float, desired: int, price: float, cfg) -> tuple[int, float]:
    shares = desired // 100 * 100
    while shares >= 100:
        fee = commission(shares * price, cfg)
        if shares * price + fee <= cash + 1e-9:
            return shares, fee
        shares -= 100
    return 0, 0.0


def rebalance_starts(panel: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp,
                     frequency: str = "quarterly") -> set[pd.Timestamp]:
    data = panel[(panel["date"] >= start) & (panel["date"] <= end)]
    if frequency not in FREQUENCIES:
        raise ValueError(f"不支持的再平衡频率：{frequency}")
    return set(data.groupby(data["date"].dt.to_period(FREQUENCIES[frequency]), sort=False).head(1)["date"])


def simulate(panel: pd.DataFrame, dividends: dict[pd.Timestamp, dict[str, float]], cfg,
             stock_weight: float = 0.5, frequency: str = "quarterly"):
    data = panel[(panel["date"] >= cfg.start) & (panel["date"] <= cfg.end)].reset_index(drop=True)
    if len(data) < 2:
        raise RuntimeError("回测区间没有足够共同交易日")
    if not 0 < stock_weight < 1:
        raise ValueError("510300 权重必须在 0 和 1 之间")
    target_weights = {"510300": stock_weight, "518880": 1.0 - stock_weight}
    cash = float(cfg.account)
    shares = {code: 0 for code in ASSETS}
    trades: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    scheduled = rebalance_starts(panel, cfg.start, cfg.end, frequency)
    dividend_cash = 0.0

    for _, row in data.iterrows():
        day = row.date
        for code, per_share in dividends.get(day, {}).items():
            amount = shares[code] * per_share
            if amount:
                cash += amount
                dividend_cash += amount
                trades.append({"date": day.date(), "event": "dividend", "code": code,
                               "price": None, "shares": shares[code], "commission": 0.0,
                               "cash_after": round(cash, 2), "amount": round(amount, 2)})
        if day in scheduled:
            nav = cash + sum(shares[c] * float(row[f"open_{c}"]) for c in ASSETS)
            desired = {c: int((nav * target_weights[c]) / float(row[f"open_{c}"]) // 100 * 100)
                       for c in ASSETS}
            if all(shares[c] == 0 for c in ASSETS) and any(desired[c] < 100 for c in ASSETS):
                raise RuntimeError("初始目标仓位不能买到两只 ETF 的整手")
            for code in ASSETS:
                excess = max(0, shares[code] - desired[code])
                if excess >= 100:
                    price = float(row[f"open_{code}"])
                    fee = commission(excess * price, cfg)
                    cash += excess * price - fee
                    shares[code] -= excess
                    trades.append({"date": day.date(), "event": "sell", "code": code, "price": round(price, 4),
                                   "shares": excess, "commission": round(fee, 2), "cash_after": round(cash, 2),
                                   "amount": round(excess * price, 2)})
            for code in ASSETS:
                deficit = max(0, desired[code] - shares[code])
                if deficit >= 100:
                    price = float(row[f"open_{code}"])
                    quantity, fee = buy_limited(cash, deficit, price, cfg)
                    if quantity:
                        cash -= quantity * price + fee
                        shares[code] += quantity
                        trades.append({"date": day.date(), "event": "buy", "code": code, "price": round(price, 4),
                                       "shares": quantity, "commission": round(fee, 2), "cash_after": round(cash, 2),
                                       "amount": round(quantity * price, 2)})
        equity = cash + sum(shares[c] * float(row[f"close_{c}"]) for c in ASSETS)
        equity_rows.append({"date": day.date(), "equity": round(equity, 2), "cash": round(cash, 2),
                            **{f"shares_{c}": shares[c] for c in ASSETS}})

    trades_frame = pd.DataFrame(trades)
    curve = pd.DataFrame(equity_rows)
    terminal = float(curve.iloc[-1].equity)
    years = (pd.Timestamp(curve.iloc[-1].date) - pd.Timestamp(curve.iloc[0].date)).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 else None
    dd = curve["equity"] / curve["equity"].cummax() - 1
    summary = {
        "start_date": str(curve.iloc[0].date), "end_date": str(curve.iloc[-1].date),
        "stock_weight": stock_weight, "rebalance_frequency": frequency,
        "terminal_equity": round(terminal, 2), "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "max_drawdown_pct": round(float(dd.min()) * 100, 2),
        "total_dividend_cash": round(dividend_cash, 2),
        "total_commission": round(float(trades_frame["commission"].sum()), 2) if not trades_frame.empty else 0.0,
        "trades": int(len(trades_frame)), "end_cash": round(cash, 2), "end_shares": shares,
    }
    return trades_frame, curve, summary


def buy_hold(panel: pd.DataFrame, dividends: dict[pd.Timestamp, dict[str, float]], cfg) -> dict[str, Any]:
    data = panel[(panel["date"] >= cfg.start) & (panel["date"] <= cfg.end)].reset_index(drop=True)
    entry = float(data.iloc[0]["open_510300"])
    shares = int(cfg.account / (entry * (1 + cfg.fee_rate)) // 100 * 100)
    cash = cfg.account - shares * entry - commission(shares * entry, cfg)
    dividend_cash = 0.0
    values = []
    for _, row in data.iterrows():
        if "510300" in dividends.get(row.date, {}):
            amount = shares * dividends[row.date]["510300"]
            cash += amount
            dividend_cash += amount
        values.append(cash + shares * float(row.close_510300))
    equity = pd.Series(values)
    terminal = float(equity.iloc[-1])
    years = (data.iloc[-1].date - data.iloc[0].date).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 else None
    dd = equity / equity.cummax() - 1
    return {"terminal_equity": round(terminal, 2), "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
            "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
            "max_drawdown_pct": round(float(dd.min()) * 100, 2), "dividend_cash": round(dividend_cash, 2)}


def parse_args():
    parser = argparse.ArgumentParser(description="两资产 ETF 未复权价格 + 现金分红审计")
    parser.add_argument("--start", type=lambda value: pd.Timestamp(value).normalize(), required=True)
    parser.add_argument("--end", type=lambda value: pd.Timestamp(value).normalize(), required=True)
    parser.add_argument("--account", type=float, default=20_000)
    parser.add_argument("--fee-rate", type=float, default=0.00025)
    parser.add_argument("--min-fee", type=float, default=5.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    cfg = parser.parse_args()
    if not cfg.start < cfg.end or cfg.account <= 0 or cfg.fee_rate < 0 or cfg.min_fee < 0:
        parser.error("时间、账户或费用参数无效")
    return cfg


def main() -> None:
    cfg = parse_args()
    panel = load_panel(cfg)
    dividends = dividend_schedule(cfg.end)
    trades, equity, strategy = simulate(panel, dividends, cfg)
    passive = buy_hold(panel, dividends, cfg)
    result = {"hypothesis": "two_asset_etf_v1_raw_total_return_audit", "data": "腾讯未复权日线 + 新浪现金分红",
              "assumptions": {key: (str(value) if isinstance(value, (Path, pd.Timestamp)) else value)
                              for key, value in vars(cfg).items()},
              "strategy": strategy, "buy_and_hold_510300_reference": passive,
              "caveats": ["分红日期和到账时间可能与券商存在细微差异", "未模拟盘口滑点、跟踪误差、申赎或停牌"]}
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    trades.to_csv(cfg.output_dir / f"trades_{stem}.csv", index=False, encoding="utf-8-sig")
    equity.to_csv(cfg.output_dir / f"equity_{stem}.csv", index=False, encoding="utf-8-sig")
    (cfg.output_dir / f"summary_{stem}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("===== 未复权 + 现金分红审计 =====")
    print(f"策略：期末 {strategy['terminal_equity']} 元，年化 {strategy['cagr_pct']}%，最大回撤 {strategy['max_drawdown_pct']}%，"
          f"分红现金 {strategy['total_dividend_cash']} 元，佣金 {strategy['total_commission']} 元")
    print(f"510300 买入持有：期末 {passive['terminal_equity']} 元，年化 {passive['cagr_pct']}%，"
          f"最大回撤 {passive['max_drawdown_pct']}%，分红现金 {passive['dividend_cash']} 元")
    print(f"输出目录：{cfg.output_dir}")


if __name__ == "__main__":
    main()

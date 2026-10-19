"""探索性候选六：2 万元可执行的 510300/518880 固定等权季度再平衡。"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

import backtest as B


ASSETS = {"510300": "sh510300", "518880": "sh518880"}
BENCHMARK = "510300"


@dataclass
class Holding:
    shares: int = 0


def commission(amount: float, cfg) -> float:
    return max(cfg.min_fee, amount * cfg.fee_rate)


def execution_price(open_price: float, side: str, cfg) -> float:
    """压力测试可加入单边滑点；默认 0，不改变已保存的基线结果。"""
    multiplier = 1 + cfg.slippage_bps / 10_000 if side == "buy" else 1 - cfg.slippage_bps / 10_000
    return open_price * multiplier


def load_panel(cfg) -> pd.DataFrame:
    panel: pd.DataFrame | None = None
    for code, symbol in ASSETS.items():
        history = B.load_history(code, pd.Timestamp("20130101"), cfg.end,
                                 cfg.cache_dir, cfg.refresh, symbol)
        if history is None:
            raise RuntimeError(f"无法取得 {code} 的腾讯日线")
        part = history[["date", "open", "close", "volume"]].rename(
            columns={"open": f"open_{code}", "close": f"close_{code}", "volume": f"volume_{code}"})
        panel = part if panel is None else panel.merge(part, on="date", how="inner")
    assert panel is not None
    panel = panel.sort_values("date").reset_index(drop=True)
    invalid = [code for code in ASSETS if (panel[f"volume_{code}"] <= 0).any()]
    if invalid:
        raise RuntimeError(f"共同交易日存在零/负成交量，不能假设可成交：{','.join(invalid)}")
    return panel


def buy_limited(cash: float, desired: int, price: float, cfg) -> tuple[int, float]:
    shares = desired // 100 * 100
    while shares >= 100:
        amount = shares * price
        fee = commission(amount, cfg)
        if amount + fee <= cash + 1e-9:
            return shares, fee
        shares -= 100
    return 0, 0.0


def rebalance_days(panel: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> set[pd.Timestamp]:
    data = panel[(panel["date"] >= start) & (panel["date"] <= end)]
    return set(data.groupby(data["date"].dt.to_period("Q"), sort=False).head(1)["date"])


def simulate(panel: pd.DataFrame, cfg) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    data = panel[(panel["date"] >= cfg.start) & (panel["date"] <= cfg.end)].reset_index(drop=True)
    if len(data) < 2:
        raise RuntimeError("回测区间没有足够共同交易日")
    initial = data.iloc[0]
    per_asset = cfg.account / 2
    impossible = [code for code in ASSETS if per_asset < 100 * float(initial[f"open_{code}"])]
    if impossible:
        raise RuntimeError(f"2 万元账户无法为 {','.join(impossible)} 建立 50% 整手仓位")

    scheduled = rebalance_days(panel, cfg.start, cfg.end)
    cash = float(cfg.account)
    holdings = {code: Holding() for code in ASSETS}
    events: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []

    for _, row in data.iterrows():
        day = row.date
        if day in scheduled:
            nav = cash + sum(holdings[c].shares * float(row[f"open_{c}"]) for c in ASSETS)
            desired = {c: int((nav / 2) / float(row[f"open_{c}"]) // 100 * 100) for c in ASSETS}
            for code in ASSETS:  # sell excess first
                held = holdings[code]
                excess = max(0, held.shares - desired[code])
                if excess >= 100:
                    price = execution_price(float(row[f"open_{code}"]), "sell", cfg)
                    fee = commission(excess * price, cfg)
                    cash += excess * price - fee
                    held.shares -= excess
                    events.append({"date": day.date(), "side": "sell", "code": code,
                                   "price": round(price, 4), "shares": excess,
                                   "commission": round(fee, 2), "cash_after": round(cash, 2)})
            for code in ASSETS:  # then buy up to target, within remaining cash
                held = holdings[code]
                deficit = max(0, desired[code] - held.shares)
                if deficit >= 100:
                    price = execution_price(float(row[f"open_{code}"]), "buy", cfg)
                    shares, fee = buy_limited(cash, deficit, price, cfg)
                    if shares:
                        cash -= shares * price + fee
                        held.shares += shares
                        events.append({"date": day.date(), "side": "buy", "code": code,
                                       "price": round(price, 4), "shares": shares,
                                       "commission": round(fee, 2), "cash_after": round(cash, 2)})
        equity = cash + sum(holdings[c].shares * float(row[f"close_{c}"]) for c in ASSETS)
        curve.append({"date": day.date(), "equity": round(equity, 2), "cash": round(cash, 2),
                      **{f"shares_{c}": holdings[c].shares for c in ASSETS}})

    trades, equity = pd.DataFrame(events), pd.DataFrame(curve)
    terminal = float(equity.iloc[-1].equity)
    years = (pd.Timestamp(equity.iloc[-1].date) - pd.Timestamp(equity.iloc[0].date)).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 else None
    drawdown = equity["equity"] / equity["equity"].cummax() - 1
    return trades, equity, {
        "start_date": str(equity.iloc[0].date), "end_date": str(equity.iloc[-1].date),
        "terminal_equity": round(terminal, 2),
        "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "scheduled_rebalances": len(scheduled),
        "actual_trades": int(len(trades)),
        "total_commission": round(float(trades["commission"].sum()), 2) if not trades.empty else 0.0,
        "end_shares": {code: holdings[code].shares for code in ASSETS},
        "end_cash": round(cash, 2),
    }


def buy_hold_510300(panel: pd.DataFrame, cfg) -> dict[str, Any]:
    data = panel[(panel["date"] >= cfg.start) & (panel["date"] <= cfg.end)].reset_index(drop=True)
    entry = execution_price(float(data.iloc[0]["open_510300"]), "buy", cfg)
    shares = int(cfg.account / (entry * (1 + cfg.fee_rate)) // 100 * 100)
    fee = commission(shares * entry, cfg)
    cash = cfg.account - shares * entry - fee
    equity = cash + shares * data["close_510300"]
    dd = equity / equity.cummax() - 1
    terminal = float(equity.iloc[-1])
    years = (data.iloc[-1].date - data.iloc[0].date).days / 365.25
    cagr = (terminal / cfg.account) ** (1 / years) - 1 if years > 0 else None
    return {"terminal_equity": round(terminal, 2),
            "total_return_pct": round((terminal / cfg.account - 1) * 100, 2),
            "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
            "max_drawdown_pct": round(float(dd.min()) * 100, 2)}


def parse_args():
    parser = argparse.ArgumentParser(description="510300/518880 固定等权季度再平衡（探索性）")
    parser.add_argument("--start", type=lambda x: pd.Timestamp(x).normalize(), required=True)
    parser.add_argument("--end", type=lambda x: pd.Timestamp(x).normalize(), required=True)
    parser.add_argument("--account", type=float, default=20_000)
    parser.add_argument("--fee-rate", type=float, default=0.00025)
    parser.add_argument("--min-fee", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=0.0,
                        help="单边滑点基点；默认 0，仅用于压力测试")
    parser.add_argument("--cache-dir", type=Path, default=Path("../backtest_cache/tencent_daily"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true")
    cfg = parser.parse_args()
    if (not cfg.start < cfg.end or cfg.account <= 0 or cfg.fee_rate < 0 or cfg.min_fee < 0
            or cfg.slippage_bps < 0 or cfg.slippage_bps >= 10_000):
        parser.error("时间、账户或费用参数无效")
    return cfg


def main() -> None:
    cfg = parse_args()
    panel = load_panel(cfg)
    trades, equity, strategy = simulate(panel, cfg)
    passive = buy_hold_510300(panel, cfg)
    result = {"hypothesis": "two_asset_etf_v1_exploratory", "assets": ASSETS,
              "data_adjustment": "qfq",
              "assumptions": {k: (str(v) if isinstance(v, (Path, pd.Timestamp)) else v)
                              for k, v in vars(cfg).items()},
              "strategy": strategy, "buy_and_hold_510300_reference": passive,
              "caveats": ["探索性历史结果：不能视为盲样本外验证", "前复权价格近似分红再投资",
                          "未模拟滑点、跟踪误差、申赎与停牌；实际费用变化须重跑"]}
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    trades.to_csv(cfg.output_dir / f"trades_{stem}.csv", index=False, encoding="utf-8-sig")
    equity.to_csv(cfg.output_dir / f"equity_{stem}.csv", index=False, encoding="utf-8-sig")
    (cfg.output_dir / f"summary_{stem}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("===== 510300/518880 固定等权（探索性）=====")
    print(f"策略：期末 {strategy['terminal_equity']} 元，收益 {strategy['total_return_pct']}%，年化 {strategy['cagr_pct']}%，最大回撤 {strategy['max_drawdown_pct']}%，佣金 {strategy['total_commission']} 元")
    print(f"510300 买入持有：期末 {passive['terminal_equity']} 元，收益 {passive['total_return_pct']}%，年化 {passive['cagr_pct']}%，最大回撤 {passive['max_drawdown_pct']}%")
    print(f"输出目录：{cfg.output_dir}")


if __name__ == "__main__":
    main()

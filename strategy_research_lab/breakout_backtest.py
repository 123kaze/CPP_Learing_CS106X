"""研究候选二：中期相对强度的新高突破（仅作回测研究，不构成投资建议）。

固定规则和冻结/验证纪律见 HYPOTHESIS_BREAKOUT_V1.md。这个脚本刻意不复用当前
test.py 的信号函数：它是不同的、需要被独立证伪的假设；但复用 backtest.py 的腾讯数据
缓存、一字涨跌停、T+1 和费用定义，避免用较宽松的执行假设美化新候选。
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

import backtest as B
import strategy as S


def add_indicators(history: pd.DataFrame) -> pd.DataFrame:
    f = S.add_indicators(history)
    f["ema200"] = S.ema(f["close"], 200)
    # 120-20 动量：最近约一个月不参与评分，避免把短期反转直接当作趋势。
    f["strength_120_20"] = f["close"].shift(20) / f["close"].shift(120) - 1
    f["prior_high55"] = f["high"].shift(1).rolling(55).max()
    f["prior_volume20"] = f["volume"].shift(1).rolling(20).mean()
    return f


def market_regime(index_history: pd.DataFrame) -> dict[pd.Timestamp, bool]:
    f = S.add_indicators(index_history)
    f["ema200"] = S.ema(f["close"], 200)
    f["return20"] = f["close"].pct_change(20)
    ok = (f["close"] > f["ema200"]) & (f["return20"] > 0)
    return pd.Series(ok.to_numpy(), index=f["date"]).to_dict()


def strength_thresholds(histories: dict[str, pd.DataFrame]) -> pd.Series:
    values = {}
    for code, history in histories.items():
        f = add_indicators(history)
        values[code] = f.set_index("date")["strength_120_20"]
    # 横截面前 10%，每个交易日只用当日及以前的日线数据。
    return pd.DataFrame(values).sort_index().quantile(0.90, axis=1, interpolation="lower")


def position_size(entry: float, stop: float, cfg) -> tuple[int, float | None]:
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return 0, None
    risk_money = cfg.account * cfg.risk
    shares = int(min(risk_money / risk_per_share,
                     risk_money / (entry * cfg.worst_gap)) // 100 * 100)
    cost_r = (S.round_trip_cost(shares, entry, stop, cfg) / (shares * risk_per_share)
              if shares >= 100 else None)
    return shares, cost_r


def evaluate_signal(f: pd.DataFrame, i: int, threshold: float, cfg) -> dict[str, Any] | None:
    if i < 200 or i >= len(f):
        return None
    t = f.iloc[i]
    required = ("atr14", "strength_120_20", "prior_high55", "prior_volume20", "ema50", "ema200")
    if any(pd.isna(t[x]) for x in required):
        return None
    if not (t.volume > 0 and t.day_change < 9.5):
        return None
    if not (t.strength_120_20 >= threshold and t.close > t.ema50 > t.ema200):
        return None
    if not (t.close >= t.prior_high55 and t.volume >= 1.5 * t.prior_volume20):
        return None

    entry = round(float(t.high) + 0.01, 2)
    stop = round(entry - 2.0 * float(t.atr14), 2)
    shares, cost_r = position_size(entry, stop, cfg)
    if stop <= 0 or entry <= stop:
        return None
    return {
        "signal_date": t.date,
        "strength_120_20": float(t.strength_120_20),
        "trigger": entry,
        "max_entry": round(entry * (1 + cfg.max_chase), 2),
        "stop": stop,
        "risk": entry - stop,
        "stop_pct": (entry - stop) / entry * 100,
        "shares": shares,
        "cost_ratio": cost_r,
        "selectable": shares >= 100 and cost_r is not None and cost_r <= cfg.max_cost_r,
        "triggered": False,
    }


def simulate_trade(f: pd.DataFrame, i: int, sig: dict[str, Any], cfg) -> dict[str, Any] | None:
    """次日突破进场；T+1 后检查初始/追踪止损。追踪高点只使用前一天已知数据。"""
    entry_i = i + 1
    if entry_i >= len(f):
        return None
    bar = f.iloc[entry_i]
    if bar.high < sig["trigger"] or bar.open > sig["max_entry"]:
        return None
    if B.is_one_price_limit(bar, f.iloc[i].close, "up"):
        return None

    entry = round(max(sig["trigger"], float(bar.open)), 2)
    initial_stop = sig["stop"]
    last = min(entry_i + cfg.hold_days - 1, len(f) - 1)
    high_water = entry  # 买入日的盘中高点先后未知，不预先抬高止损。
    pending_limit_down = False
    status: str | None = None
    exit_i: int | None = None
    exit_price: float | None = None

    for k in range(entry_i + 1, len(f)):
        b = f.iloc[k]
        previous = f.iloc[k - 1]
        locked = B.is_one_price_limit(b, previous.close, "down")
        # 今天盘前仅用昨天收盘后能知道的高点和 ATR 更新止损。
        high_water = max(high_water, float(previous.high))
        trail = max(initial_stop, high_water - 3.0 * float(previous.atr14))
        if pending_limit_down:
            if locked:
                continue
            status, exit_i, exit_price = "forced_exit_after_limit_down", k, float(b.open)
            break
        if k > last:
            break
        if b.open <= trail:
            if locked:
                pending_limit_down = True
                continue
            status, exit_i, exit_price = "gap_stop", k, float(b.open)
            break
        if b.low <= trail:
            status, exit_i, exit_price = "trail_stop", k, trail
            break

    if status is None:
        if pending_limit_down or last <= entry_i or entry_i + cfg.hold_days - 1 > len(f) - 1:
            status, exit_i = "open_at_data_end", len(f) - 1
        else:
            final_bar = f.iloc[last]
            if B.is_one_price_limit(final_bar, f.iloc[last - 1].close, "down"):
                for k in range(last + 1, len(f)):
                    if not B.is_one_price_limit(f.iloc[k], f.iloc[k - 1].close, "down"):
                        status, exit_i, exit_price = "forced_exit_after_limit_down", k, float(f.iloc[k].open)
                        break
                if status is None:
                    status, exit_i = "open_at_data_end", len(f) - 1
            else:
                status, exit_i, exit_price = "timeout", last, float(final_bar.close)

    if exit_i is None:
        raise RuntimeError("模拟交易缺少出场日期")
    if exit_price is None:
        gross = cost = net = net_r = None
    else:
        gross = sig["shares"] * (exit_price - entry)
        cost = S.round_trip_cost(sig["shares"], entry, exit_price, cfg)
        net = gross - cost
        net_r = net / (sig["shares"] * sig["risk"])
    return {
        "entry_date": f.iloc[entry_i].date,
        "exit_date": f.iloc[exit_i].date,
        "status": status,
        "entry_price": entry,
        "exit_price": None if exit_price is None else round(exit_price, 2),
        "holding_days": exit_i - entry_i + 1,
        "gross_pnl": None if gross is None else round(gross, 2),
        "cost": None if cost is None else round(cost, 2),
        "net_pnl": None if net is None else round(net, 2),
        "net_r": None if net_r is None else round(net_r, 3),
    }


def backtest_symbol(code: str, name: str, history: pd.DataFrame, thresholds: pd.Series,
                    regime: dict[pd.Timestamp, bool], cfg) -> list[dict[str, Any]]:
    f = add_indicators(history)
    out: list[dict[str, Any]] = []
    for i in range(200, len(f) - 1):
        day = f.at[i, "date"]
        if not (cfg.start <= day <= cfg.end) or not regime.get(day, False):
            continue
        threshold = thresholds.get(day)
        if pd.isna(threshold):
            continue
        sig = evaluate_signal(f, i, float(threshold), cfg)
        if sig is None:
            continue
        rec = {"code": code, "name": name, **sig}
        trade = simulate_trade(f, i, sig, cfg) if sig["shares"] >= 100 else None
        if trade is not None:
            rec.update(trade)
            rec["triggered"] = True
        out.append(rec)
    return out


def portfolio(signals: pd.DataFrame, cfg) -> pd.DataFrame:
    """同一信号日只挂强度最高的两只；未触发时不递补；资金和持仓都受约束。"""
    held: list[dict[str, Any]] = []
    taken: list[pd.Series] = []
    ordered = signals.sort_values(["signal_date", "strength_120_20"], ascending=[True, False])
    for day, group in ordered.groupby("signal_date"):
        held = [x for x in held if x["exit_date"] > day]
        free = cfg.max_positions - len(held)
        if free <= 0:
            continue
        held_codes = {x["code"] for x in held}
        candidates = group[group["selectable"] & ~group["code"].isin(held_codes)].head(min(free, cfg.max_picks))
        cash_used = sum(x["notional"] for x in held)
        for _, row in candidates.iterrows():
            if not row["triggered"]:
                continue
            notional = row["shares"] * row["entry_price"]
            if cash_used + notional > cfg.account:
                continue
            cash_used += notional
            held.append({"code": row["code"], "exit_date": row["exit_date"], "notional": notional})
            taken.append(row)
    return pd.DataFrame(taken)


def stats(trades: pd.DataFrame, cfg) -> dict[str, Any]:
    if trades.empty:
        return {"trades": 0, "closed_trades": 0}
    closed = trades[trades["net_r"].notna()].sort_values("exit_date")
    if closed.empty:
        return {"trades": int(len(trades)), "closed_trades": 0}
    daily = closed.groupby("exit_date")["net_pnl"].sum()
    equity = cfg.account + daily.cumsum()
    drawdown = B.max_drawdown(pd.concat([pd.Series([cfg.account]), equity.reset_index(drop=True)]))
    years: dict[str, dict[str, Any]] = {}
    for year, group in closed.groupby(pd.to_datetime(closed["signal_date"]).dt.year):
        cumulative = group.groupby("exit_date")["net_pnl"].sum().sort_index().cumsum()
        years[str(year)] = {
            "trades": int(len(group)),
            "mean_net_r": round(float(group["net_r"].mean()), 3),
            "net_pnl": round(float(group["net_pnl"].sum()), 2),
            "max_drawdown_yuan": round(B.max_drawdown(pd.concat([pd.Series([0.0]), cumulative.reset_index(drop=True)])), 2),
        }
    return {
        "trades": int(len(trades)),
        "closed_trades": int(len(closed)),
        "net_positive_rate_pct": round(float((closed["net_pnl"] > 0).mean() * 100), 2),
        "mean_net_r": round(float(closed["net_r"].mean()), 3),
        "total_net_pnl": round(float(closed["net_pnl"].sum()), 2),
        "total_return_pct": round(float(closed["net_pnl"].sum()) / cfg.account * 100, 2),
        "total_cost": round(float(closed["cost"].sum()), 2),
        "max_drawdown_yuan": round(drawdown, 2),
        "max_drawdown_pct_of_account": round(drawdown / cfg.account * 100, 2),
        "status_counts": {str(k): int(v) for k, v in trades["status"].value_counts().items()},
        "yearly": years,
    }


def parse_timestamp_or_none(value: str) -> pd.Timestamp | None:
    return None if value.lower() in {"none", "off"} else pd.Timestamp(value).normalize()


def parse_args():
    p = argparse.ArgumentParser(description="研究候选二：中期相对强度的新高突破回测")
    p.add_argument("--start", type=lambda x: pd.Timestamp(x).normalize(), required=True)
    p.add_argument("--end", type=lambda x: pd.Timestamp(x).normalize(), required=True)
    p.add_argument("--holdout-start", type=parse_timestamp_or_none, default=None,
                   help="形成期填 none；通过形成期门槛后才填写样本外开始日")
    p.add_argument("--account", type=float, default=20_000)
    p.add_argument("--risk", type=float, default=0.005)
    p.add_argument("--worst-gap", type=float, default=0.10)
    p.add_argument("--max-chase", type=float, default=0.01)
    p.add_argument("--fee-rate", type=float, default=0.00025)
    p.add_argument("--min-fee", type=float, default=5.0)
    p.add_argument("--stamp", type=float, default=0.0005)
    p.add_argument("--max-cost-r", type=float, default=0.20)
    p.add_argument("--hold-days", type=int, default=40)
    p.add_argument("--max-positions", type=int, default=2)
    p.add_argument("--max-picks", type=int, default=2)
    p.add_argument("--market-symbol", default="sh000985")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--cache-dir", type=Path, default=Path("../backtest_cache/tencent_daily"))
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--max-symbols", type=int, help="仅用于烟雾测试，不可用于策略判断")
    cfg = p.parse_args()
    if not (cfg.start < cfg.end):
        p.error("--start 必须早于 --end")
    if cfg.holdout_start is not None and not (cfg.start <= cfg.holdout_start <= cfg.end):
        p.error("--holdout-start 必须在回测区间内")
    if not (cfg.account > 0 and 0 < cfg.risk < 1 and 0 < cfg.worst_gap < 1):
        p.error("账户、风险和最坏跳空参数无效")
    if min(cfg.max_chase, cfg.fee_rate, cfg.min_fee, cfg.stamp, cfg.max_cost_r) < 0:
        p.error("费用和追价参数不能为负")
    if min(cfg.hold_days, cfg.max_positions, cfg.max_picks, cfg.workers) < 1:
        p.error("持有天数、持仓数、候选数和并发数至少为 1")
    return cfg


def formation_pass(result: dict[str, Any]) -> dict[str, Any]:
    """仅形成期使用；门槛已经写入假设文件，不能看结果后修改。"""
    portfolio_stats = result["portfolio"]
    yearly = portfolio_stats.get("yearly", {})
    expected_years = [str(year) for year in range(result["start"].year, result["end"].year + 1)]
    each_year_positive = all(yearly.get(y, {}).get("mean_net_r", 0) > 0 for y in expected_years)
    passed = (portfolio_stats.get("closed_trades", 0) >= 40
              and portfolio_stats.get("mean_net_r", 0) > 0
              and each_year_positive)
    return {
        "rule": "形成期 >= 40 笔、整体平均净 R > 0，且每个自然年平均净 R > 0",
        "passed": passed,
        "each_year_positive": each_year_positive,
        "expected_years": expected_years,
    }


def holdout_gate(portfolio_stats: dict[str, Any], cfg) -> dict[str, Any]:
    if cfg.holdout_start is None:
        return {"applicable": False, "passed": None,
                "reason": "形成期模式：未设置样本外段，不作样本外判定"}
    start_year, end_year = cfg.holdout_start.year, cfg.end.year
    by_year = {str(year): portfolio_stats.get("yearly", {}).get(str(year), {})
               for year in range(start_year, end_year + 1)}
    # 本 v1 的样本外命令会只给 2025+，所以 portfolio 就是样本外集合。
    year_positive = {y: (v.get("trades", 0) > 0 and v.get("mean_net_r", 0) > 0) for y, v in by_year.items()}
    passed = (portfolio_stats.get("closed_trades", 0) >= 20
              and portfolio_stats.get("mean_net_r", 0) >= 0.2
              and all(year_positive.values()))
    return {
        "applicable": True,
        "rule": "每个样本外自然年平均净 R > 0、整体平均净 R >= 0.2、至少 20 笔",
        "year_positive": year_positive,
        "passed": passed,
    }


def main() -> None:
    cfg = parse_args()
    # EMA200 需要较长预热。现有腾讯缓存从 2021-06-15 起；在该数据可得性下，
    # 2022 年最初约数月会自然处于预热期而不产生信号，不能把它误解为“零交易”。
    data_start = cfg.start - pd.Timedelta(days=200)
    data_end = min(cfg.end + pd.Timedelta(days=70), pd.Timestamp(date.today()))
    print(f"信号区间：{cfg.start:%Y-%m-%d} 至 {cfg.end:%Y-%m-%d}")
    universe = B.load_current_main_board()
    print(f"当前主板清单：{len(universe)} 只（按当前名称排除 ST/退）")
    histories, failed = B.collect_histories(universe, cfg, data_start, data_end)
    if not histories:
        raise RuntimeError("没有取得任何股票历史数据")
    market_history = B.load_history(f"market_{cfg.market_symbol}", data_start, data_end,
                                    cfg.cache_dir, cfg.refresh, cfg.market_symbol)
    if market_history is None or len(market_history) < 200:
        raise RuntimeError(f"无法取得 {cfg.market_symbol} 的足够指数日线")
    regime = market_regime(market_history)
    print(f"市场状态合格日：{sum(regime.values())}/{len(regime)}")
    print("计算逐日 120-20 相对强度前 10% 门槛……")
    thresholds = strength_thresholds(histories)
    names = universe.set_index("code")["name"].to_dict()
    records: list[dict[str, Any]] = []
    for number, (code, history) in enumerate(histories.items(), 1):
        records.extend(backtest_symbol(code, names[code], history, thresholds, regime, cfg))
        if number == 1 or number % 500 == 0 or number == len(histories):
            print(f"  回测 {number}/{len(histories)}；累计信号 {len(records)}", flush=True)
    signals = pd.DataFrame(records)
    if signals.empty:
        raise RuntimeError("区间内没有候选信号")
    for column in ("entry_date", "exit_date", "status", "entry_price", "exit_price", "net_pnl", "net_r", "cost"):
        if column not in signals:
            signals[column] = None
    taken = portfolio(signals, cfg)
    result: dict[str, Any] = {
        "hypothesis": "breakout_v1",
        "start": cfg.start,
        "end": cfg.end,
        "universe_with_history": len(histories),
        "history_download_failed": len(failed),
        "signals": int(len(signals)),
        "selectable_signals": int(signals["selectable"].sum()),
        "portfolio": stats(taken, cfg),
        "assumptions": {key: (str(value) if isinstance(value, (Path, pd.Timestamp)) else value)
                        for key, value in vars(cfg).items()},
        "known_bias": ["存活偏差：只有当前上市股票", "ST 按今天名称剔除，有未来信息",
                          "日线无法确定盘中先后；追踪止损只在下一日生效", "未模拟排队、冲击成本和行业集中度"],
    }
    result["formation_gate"] = formation_pass(result) if cfg.holdout_start is None else None
    result["holdout_gate"] = holdout_gate(result["portfolio"], cfg)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    signals.to_csv(cfg.output_dir / f"signals_{stem}.csv", index=False, encoding="utf-8-sig")
    if not taken.empty:
        taken.to_csv(cfg.output_dir / f"portfolio_trades_{stem}.csv", index=False, encoding="utf-8-sig")
    (cfg.output_dir / f"summary_{stem}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    s = result["portfolio"]
    print("\n===== 组合结果 =====")
    print(f"成交 {s.get('trades', 0)} 笔；平均净 R {s.get('mean_net_r')}；总收益 {s.get('total_return_pct')}%；"
          f"最大回撤 {s.get('max_drawdown_pct_of_account')}%")
    for year, values in s.get("yearly", {}).items():
        print(f"  {year}：{values['trades']} 笔，平均 R {values['mean_net_r']}，净盈亏 {values['net_pnl']} 元")
    if result["formation_gate"] is not None:
        gate = result["formation_gate"]
        print("\n形成期门槛：" + ("通过；才允许进行一次样本外运行。" if gate["passed"]
                                  else "不通过；拒绝 breakout_v1，禁止查看此假设的样本外输出。"))
    print(f"输出目录：{cfg.output_dir}")


if __name__ == "__main__":
    main()

"""强势股回调策略的共用规则。test.py（每日选股）和 backtest.py（回测）都从这里导入，
保证回测的就是实际在跑的规则。改规则只改这一个文件。

日线输入列：date, open, high, low, close, volume（前复权）。
60 日涨幅排名不在这里做：选股用腾讯实时行情的 60 日涨跌幅，回测按当日全市场横截面计算。
"""
from __future__ import annotations

import argparse
import math
from typing import Any

import pandas as pd


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """在日线上加 EMA21/EMA50、ATR14、当日涨幅、60 日涨幅。返回新表，索引为 0..n-1。"""
    f = frame.reset_index(drop=True).copy()
    f["ema21"] = ema(f["close"], 21)
    f["ema50"] = ema(f["close"], 50)
    prev_close = f["close"].shift(1)
    f["day_change"] = f["close"].pct_change() * 100
    f["return60"] = f["close"].pct_change(60)
    f["atr14"] = pd.concat(
        [f["high"] - f["low"], (f["high"] - prev_close).abs(), (f["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1).rolling(14).mean()
    return f


def market_regime(index_hist: pd.DataFrame) -> pd.Series:
    """大盘开关：指数收盘 > EMA50 时允许新开仓。返回以日期为索引的布尔序列。
    这条规则在看到回测结果之前就定死了，不要根据回测结果改均线长度或换指数。"""
    f = add_indicators(index_hist)
    return pd.Series((f["close"] > f["ema50"]).to_numpy(), index=f["date"])


def round_trip_cost(shares: int, buy: float, sell: float, rules) -> float:
    """双边佣金（含最低佣金）加卖出印花税。过户费很小，忽略。"""
    buy_amt, sell_amt = shares * buy, shares * sell
    return (
        max(rules.min_fee, buy_amt * rules.fee_rate)
        + max(rules.min_fee, sell_amt * rules.fee_rate)
        + sell_amt * rules.stamp
    )


def evaluate_signal(f: pd.DataFrame, i: int, rules) -> dict[str, Any] | None:
    """检查第 i 根 K 线收盘后是否出信号（不含 60 日涨幅排名）。

    规则：
    1. 当日有成交、未涨停（涨幅 < 9.5%）
    2. 趋势：收盘 > EMA50 且 EMA21 > EMA50
    3. 回到支撑：收盘在 EMA21 上方 0~near；近 3 天最低价碰到 EMA21 的 1% 以内
    4. AVWAP（锚点为近 20 日最高点，且至少在 min_anchor_age 根之前）与 EMA21 相差
       不超过 confluence，且收盘、触发价都在 AVWAP 上方
    5. 触发价 = 当日最高 + 0.01；止损 = 当日和昨日最低中较低者 - 0.01
    6. 止损距离不超过 max_stop_atr 倍 ATR14
    7. 目标 = min(触发价 + target_r × R, 触发价 + target_atr_cap × ATR14)，且至少 min_effective_r 倍 R
    8. 股数 = min(按风险, 按一个跌停) 向下取整到 100 股；不足一手时 shares=0 照样返回
    """
    if i < 60 or i >= len(f):
        return None
    t, y = f.iloc[i], f.iloc[i - 1]
    if not (t.volume > 0) or pd.isna(t.day_change) or t.day_change >= 9.5:
        return None
    if not (t.close > t.ema50 and t.ema21 > t.ema50):
        return None
    dist = (t.close - t.ema21) / t.ema21
    if not (0 < dist <= rules.near):
        return None
    recent = f.iloc[i - 2 : i + 1]
    if not (recent["low"] <= recent["ema21"] * 1.01).any():
        return None

    look = f.iloc[i - 19 : i + 1]
    anchor = int(look["high"].idxmax())
    if anchor > i - rules.min_anchor_age:
        return None
    seg = f.iloc[anchor : i + 1]
    if seg["volume"].sum() <= 0:
        return None
    typical = (seg["high"] + seg["low"] + seg["close"]) / 3
    avwap = float((typical * seg["volume"]).sum() / seg["volume"].sum())
    if abs(avwap - t.ema21) / t.ema21 > rules.confluence or t.close <= avwap:
        return None

    trigger = round(float(t.high) + 0.01, 2)
    stop = round(min(float(t.low), float(y.low)) - 0.01, 2)
    risk = trigger - stop
    atr = float(t.atr14)
    if risk <= 0 or pd.isna(atr) or atr <= 0 or trigger <= avwap:
        return None
    if risk > rules.max_stop_atr * atr:
        return None
    raw_target = round(trigger + rules.target_r * risk, 2)
    atr_target = round(trigger + rules.target_atr_cap * atr, 2)
    target = min(raw_target, atr_target)
    effective_r = (target - trigger) / risk
    if effective_r < rules.min_effective_r:
        return None

    risk_money = rules.account * rules.risk
    shares = math.floor(min(risk_money / risk, risk_money / (trigger * rules.worst_gap)) / 100) * 100
    cost_ratio = (
        round_trip_cost(shares, trigger, stop, rules) / (shares * risk) if shares >= 100 else None
    )
    return {
        "date": t.date,
        "close": float(t.close),
        "ema21": float(t.ema21),
        "avwap": avwap,
        "atr14": atr,
        "trigger": trigger,
        "max_entry": round(trigger * (1 + rules.max_chase), 2),
        "stop": stop,
        "risk": risk,
        "stop_pct": risk / trigger * 100,
        "target": target,
        "effective_r": effective_r,
        "shares": shares,
        "cost_ratio": cost_ratio,
    }


def selectable(sig: dict[str, Any], rules) -> bool:
    """挑选规则的前两步：买得起一手，且止损时成本不超过 R 的 max_cost_r。"""
    return sig["shares"] >= 100 and sig["cost_ratio"] is not None and sig["cost_ratio"] <= rules.max_cost_r


def add_rule_args(p: argparse.ArgumentParser) -> None:
    """test.py 和 backtest.py 共用的参数，默认值只在这里定义一次。"""
    p.add_argument("--account", type=float, default=20000, help="账户资金，单位元")
    p.add_argument("--risk", type=float, default=0.005, help="单笔风险占比，默认 0.5%%")
    p.add_argument("--worst-gap", type=float, default=0.10, help="仓位计算的最坏跳空幅度，默认 10%%")
    p.add_argument("--top", type=float, default=0.10, help="按 60 日涨幅取前多少比例")
    p.add_argument("--near", type=float, default=0.03, help="收盘价高于 21日EMA 的上限")
    p.add_argument("--confluence", type=float, default=0.03, help="AVWAP 与 21日EMA 的最大偏离")
    p.add_argument("--min-anchor-age", type=int, default=3, help="AVWAP 锚点至少在几根 K 线之前")
    p.add_argument("--max-stop-atr", type=float, default=2.5, help="止损距离最多几倍 ATR14")
    p.add_argument("--target-r", type=float, default=3.0, help="止盈目标 R 倍数")
    p.add_argument("--target-atr-cap", type=float, default=4.0, help="目标最多高出触发价几倍 ATR14")
    p.add_argument("--min-effective-r", type=float, default=2.0, help="ATR 封顶后目标至少几倍 R")
    p.add_argument("--max-chase", type=float, default=0.01, help="高于触发价最多追多少，默认 1%%")
    p.add_argument("--fee-rate", type=float, default=0.00025, help="佣金率，默认万 2.5")
    p.add_argument("--min-fee", type=float, default=5.0, help="单边最低佣金，免五账户填 0")
    p.add_argument("--stamp", type=float, default=0.0005, help="卖出印花税，默认 0.05%%")
    p.add_argument("--max-cost-r", type=float, default=0.2, help="止损时成本超过 R 的多少就不选，默认 20%%")
    p.add_argument("--max-picks", type=int, default=2, help="每天最多挑几只，默认 2")
    p.add_argument("--market-filter", choices=("none", "csi_all_ema50"), default="csi_all_ema50",
                   help="大盘过滤：默认中证全指收盘必须高于 EMA50 才开新仓")
    p.add_argument("--market-symbol", default="sh000985", help="大盘过滤用的腾讯指数代码，默认中证全指")


def validate_rule_args(p: argparse.ArgumentParser, a) -> None:
    if not 0 < a.top < 1:
        p.error("--top 必须在 0 和 1 之间")
    if a.account <= 0 or not 0 < a.risk < 1 or not 0 < a.worst_gap < 1:
        p.error("--account 必须大于 0，--risk 和 --worst-gap 必须在 0 和 1 之间")
    if min(a.near, a.confluence, a.max_stop_atr, a.target_r, a.target_atr_cap, a.min_effective_r) <= 0:
        p.error("规则参数必须大于 0")
    if a.min_anchor_age < 1 or a.max_picks < 1:
        p.error("--min-anchor-age 和 --max-picks 至少为 1")
    if min(a.max_chase, a.fee_rate, a.min_fee, a.stamp, a.max_cost_r) < 0:
        p.error("费用和追价参数不能为负")
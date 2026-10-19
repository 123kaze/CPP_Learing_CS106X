"""A 股「强势股回调」策略的日线回测（腾讯证券数据源）。

用法（strategy.py 要和本文件放在同一目录）：
    python backtest.py                                  # 默认 2019-01-01 至最近交易日
    python backtest.py --start 20220101 --end 20221231  # 只测某一段
    python backtest.py --min-fee 0                      # 免五账户

首次运行要下载约 3000 只主板股票多年的日线，可能需要一两个小时；数据缓存在
backtest_cache/tencent_daily，中断后再跑会接着用。

规则与 test.py 完全相同（都来自 strategy.py），默认带大盘过滤：中证全指收盘 > EMA50
才开新仓（--market-filter none 关闭）。

预先定死的检验（只跑这一次，不过就放弃）：2025-01-01 之前为调整段，只报告；
之后为检验段，组合回测每年扣费后平均 R 都 > 0、且整段平均 R >= 0.2 才算通过。

两种统计：

1. 组合回测（主要看这个）：模拟你实际的做法。每个交易日收盘后，从当日全部信号里
   剔除买不起一手、止损成本占 R 过高的，按止损距离从小到大取前 max-picks 只挂条件单；
   同时持仓不超过 max-positions 只，资金不超过账户；没突破就作废，不替补。
   输出资金曲线、最大回撤、分年份结果。
2. 逐信号统计（参考）：每个信号独立交易，不受持仓上限约束，用来看规则本身的期望值。

成交约定：
* 入场：次日最高价达到触发价才成交；开盘高于触发价按开盘价成交；开盘高于最高委托价
  不追；一字涨停视为买不进。
* T+1：买入当天不能卖，次日起才检查止损/止盈。
* 跳空低开穿过止损按开盘价卖；一字跌停卖不出，顺延到第一个能成交的日子按开盘价卖。
* 同一根 K 线同时碰到止损和目标，按止损算（保守）。
* 持有满 hold-days 个交易日仍未出场，按当日收盘卖出（超时）。
* 成本：双边佣金（含最低佣金）+ 卖出印花税。

已知偏差（都会让结果偏好，正收益要打折看）：
* 只能拿到当前上市的股票，已退市的没有（存活偏差）。
* ST 按今天的名称剔除：后来变 ST 的被提前剔掉，当年是 ST、现在摘帽的被纳入。
* 没有行业数据，「同一板块最多 1 只」没有模拟。
本工具只用于策略研究，不构成投资建议。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import io
import json
import time
from datetime import date
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd

import strategy as S

MAIN_BOARD_PREFIX = ("600", "601", "603", "605", "000", "001", "002", "003")
RAW_COLUMNS = ["date", "open", "close", "high", "low", "volume"]


# ---------------------------------------------------------------- 数据

def tx_symbol(code: str) -> str:
    return ("sh" if code.startswith("6") else "sz") + code


def load_current_main_board() -> pd.DataFrame:
    with contextlib.redirect_stderr(io.StringIO()):
        spot = ak.stock_zh_a_spot_tx()
    spot["code"] = spot["code"].astype(str).str[-6:]
    u = spot[spot["code"].str.startswith(MAIN_BOARD_PREFIX)].copy()
    u = u[~u["name"].astype(str).str.contains("ST|退", na=False)]
    return u.drop_duplicates("code").sort_values("code").reset_index(drop=True)[["code", "name"]]


def normalize_history(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    if frame is None or frame.empty:
        return None
    frame = frame.rename(columns={"vol": "volume", "成交量": "volume"})
    if not set(RAW_COLUMNS).issubset(frame.columns):
        return None
    data = frame[RAW_COLUMNS].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    for c in RAW_COLUMNS[1:]:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data = data.dropna(subset=RAW_COLUMNS).drop_duplicates("date").sort_values("date")
    return data.reset_index(drop=True) if not data.empty else None


def load_history(code: str, data_start: pd.Timestamp, data_end: pd.Timestamp,
                 cache_dir: Path, refresh: bool, symbol: str | None = None) -> pd.DataFrame | None:
    """读取前复权日线。缓存旁边记下当时请求的区间：只要请求区间覆盖本次所需就复用，
    这样上市晚于 data_start 的股票不会每次都重新下载。"""
    cache_path = cache_dir / f"{code}.csv"
    meta_path = cache_dir / f"{code}.range.json"
    if not refresh and cache_path.exists():
        try:
            cached = normalize_history(pd.read_csv(cache_path))
            if cached is not None:
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    covered = pd.Timestamp(meta["start"]) <= data_start and pd.Timestamp(meta["end"]) >= data_end
                else:
                    # 旧版缓存没有区间记录：按数据本身的首尾日期判断（周末节假日留 7 天余量）
                    covered = (cached["date"].min() <= data_start + pd.Timedelta(days=7)
                               and cached["date"].max() >= data_end - pd.Timedelta(days=7))
                if covered:
                    return cached
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            pass

    for attempt in range(3):
        try:
            with contextlib.redirect_stderr(io.StringIO()):  # 隐藏接口自带的 tqdm
                raw = ak.stock_zh_a_hist_tx(
                    symbol=symbol or tx_symbol(code), start_date=data_start.strftime("%Y%m%d"),
                    end_date=data_end.strftime("%Y%m%d"), adjust="qfq", timeout=20,
                )
            data = normalize_history(raw)
            if data is None:
                return None
            cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = cache_path.with_suffix(".tmp")
            data.to_csv(tmp, index=False)
            tmp.replace(cache_path)
            meta_path.write_text(json.dumps({"start": str(data_start.date()), "end": str(data_end.date())}),
                                 encoding="utf-8")
            return data
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1 + attempt)
    return None


def load_market_regime(cfg, data_start: pd.Timestamp, data_end: pd.Timestamp) -> dict[pd.Timestamp, bool]:
    """读取预先指定的中证全指，并以信号日收盘价是否高于 EMA50 作为开仓开关。"""
    if cfg.market_filter == "none":
        return {}
    market = load_history(
        code=f"market_{cfg.market_symbol}",
        data_start=data_start,
        data_end=data_end,
        cache_dir=cfg.cache_dir,
        refresh=cfg.refresh,
        symbol=cfg.market_symbol,
    )
    if market is None or len(market) < 50:
        raise RuntimeError(f"无法取得市场指数 {cfg.market_symbol} 的有效日线，不能绕过大盘过滤")
    return S.market_regime(market).to_dict()


def collect_histories(universe, cfg, data_start, data_end):
    codes = universe["code"].tolist()
    if cfg.max_symbols is not None:
        codes = codes[: cfg.max_symbols]
        print(f"仅测试前 {len(codes)} 个代码；该模式的统计结果不具备代表性。")
    histories: dict[str, pd.DataFrame] = {}
    failed: list[str] = []
    print(f"下载/读取 {len(codes)} 只股票的日线缓存（并发 {cfg.workers}）……")
    print("首次下载每只要几秒，全部可能要一两个小时；中断后重跑会跳过已下载的。")
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.workers) as ex:
        futures = {ex.submit(load_history, c, data_start, data_end, cfg.cache_dir, cfg.refresh): c for c in codes}
        for n, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            code = futures[fut]
            try:
                h = fut.result()
            except Exception:
                h = None
            if h is None or len(h) < 61:
                failed.append(code)
            else:
                histories[code] = h
            if n == 1 or n % 20 == 0 or n == len(codes):
                elapsed = time.time() - t0
                eta = elapsed / n * (len(codes) - n) / 60
                print(f"  日线 {n}/{len(codes)}；有效 {len(histories)}，失败 {len(failed)}；"
                      f"已用 {elapsed / 60:.1f} 分钟，预计还要 {eta:.0f} 分钟", flush=True)
    return histories, failed


def build_return_thresholds(histories: dict[str, pd.DataFrame], top: float) -> pd.Series:
    """逐日计算全市场 60 日涨幅前 top 比例的门槛。"""
    returns = pd.DataFrame({c: f.set_index("date")["close"].pct_change(60) for c, f in histories.items()})
    return returns.sort_index().quantile(1 - top, axis=1, interpolation="lower")


# ---------------------------------------------------------------- 成交模拟

def is_one_price_limit(bar, previous_close: float, direction: str) -> bool:
    """一字涨/跌停：全天一个价。日线看不到盘口，保守视为不可成交。"""
    if abs(bar.high - bar.low) > 1e-9 or abs(bar.open - bar.close) > 1e-9:
        return False
    return bar.close > previous_close if direction == "up" else bar.close < previous_close


def simulate_trade(f: pd.DataFrame, i: int, sig: dict[str, Any], cfg) -> dict[str, Any] | None:
    """第 i 根是信号日。未成交返回 None。"""
    e = i + 1
    if e >= len(f):
        return None
    trigger, stop, target = sig["trigger"], sig["stop"], sig["target"]
    bar = f.iloc[e]
    if bar.high < trigger or bar.open > sig["max_entry"]:
        return None
    if is_one_price_limit(bar, f.iloc[i].close, "up"):
        return None
    entry_price = round(max(trigger, float(bar.open)), 2)
    shares = sig["shares"]

    planned_last = e + cfg.hold_days - 1  # 持有天数含买入当天
    last = min(planned_last, len(f) - 1)
    status, exit_i, exit_price = None, None, None
    pending_forced = False

    for k in range(e + 1, len(f)):  # T+1：买入当天不能卖
        b = f.iloc[k]
        locked = is_one_price_limit(b, f.iloc[k - 1].close, "down")
        if pending_forced:
            if locked:
                continue
            status, exit_i, exit_price = "forced_exit_after_limit_down", k, float(b.open)
            break
        if k > last:
            break
        if b.open <= stop:
            if locked:
                pending_forced = True
                continue
            status, exit_i, exit_price = "gap_stop", k, float(b.open)
            break
        if b.open >= target:  # 跳空越过目标也只按目标价算，不夸大收益
            status, exit_i, exit_price = "win", k, target
            break
        hit_stop, hit_target = b.low <= stop, b.high >= target
        if hit_stop:  # 同日两者都碰到也按止损
            status, exit_i, exit_price = ("ambiguous_loss" if hit_target else "loss"), k, stop
            break
        if hit_target:
            status, exit_i, exit_price = "win", k, target
            break

    if status is None:
        if pending_forced or planned_last > len(f) - 1 or last <= e:
            # 数据到头还没能卖出：结果未知，不计入统计
            status, exit_i = "open_at_data_end", len(f) - 1
        else:
            b = f.iloc[last]
            if is_one_price_limit(b, f.iloc[last - 1].close, "down"):
                # 到期日封死跌停，顺延到第一个能成交的日子
                for k in range(last + 1, len(f)):
                    if not is_one_price_limit(f.iloc[k], f.iloc[k - 1].close, "down"):
                        status, exit_i, exit_price = "forced_exit_after_limit_down", k, float(f.iloc[k].open)
                        break
                if status is None:
                    status, exit_i = "open_at_data_end", len(f) - 1
            else:
                status, exit_i, exit_price = "timeout", last, float(b.close)

    if exit_price is None:
        gross = cost = net = net_r = None
    else:
        gross = shares * (exit_price - entry_price)
        cost = S.round_trip_cost(shares, entry_price, exit_price, cfg)
        net = gross - cost
        net_r = net / (shares * sig["risk"])
    return {
        "entry_date": f.iloc[e].date, "exit_date": f.iloc[exit_i].date, "status": status,
        "entry_price": entry_price, "exit_price": None if exit_price is None else round(exit_price, 2),
        "holding_days": exit_i - e + 1,
        "gross_pnl": None if gross is None else round(gross, 2),
        "cost": None if cost is None else round(cost, 2),
        "net_pnl": None if net is None else round(net, 2),
        "net_r": None if net_r is None else round(net_r, 3),
    }


def backtest_symbol(code: str, name: str, history: pd.DataFrame, thresholds: pd.Series,
                    market_regime: dict[pd.Timestamp, bool], cfg):
    """返回该股票在回测区间内的全部信号（含是否成交及结果）。"""
    f = S.add_indicators(history)
    out = []
    for i in range(60, len(f) - 1):
        d = f.at[i, "date"]
        if not (cfg.start <= d <= cfg.end):
            continue
        # 信号在收盘后形成，次日才挂单，因此可无前视地使用当日大盘收盘状态。
        if cfg.market_filter != "none" and not market_regime.get(d, False):
            continue
        th = thresholds.get(d)
        r60 = f.at[i, "return60"]
        if pd.isna(th) or pd.isna(r60) or r60 < th:
            continue
        sig = S.evaluate_signal(f, i, cfg)
        if sig is None:
            continue
        rec = {
            "code": code, "name": name, "signal_date": d, "return60_pct": round(r60 * 100, 2),
            "trigger": sig["trigger"], "stop": sig["stop"], "target": round(sig["target"], 2),
            "stop_pct": round(sig["stop_pct"], 3), "effective_r": round(sig["effective_r"], 3),
            "shares": sig["shares"],
            "cost_ratio": None if sig["cost_ratio"] is None else round(sig["cost_ratio"], 3),
            "selectable": S.selectable(sig, cfg), "triggered": False,
        }
        if sig["shares"] >= 100:
            t = simulate_trade(f, i, sig, cfg)
            if t is not None:
                rec.update(t)
                rec["triggered"] = True
        out.append(rec)
    return out


# ---------------------------------------------------------------- 统计

def max_drawdown(equity: pd.Series) -> float:
    return float((equity - equity.cummax()).min()) if len(equity) else 0.0


def trade_stats(t: pd.DataFrame) -> dict[str, Any]:
    closed = t[t["net_r"].notna()]
    if closed.empty:
        return {"closed_trades": 0}
    return {
        "closed_trades": int(len(closed)),
        "target_hit_rate_pct": round(float((closed["status"] == "win").mean() * 100), 2),
        "net_positive_rate_pct": round(float((closed["net_pnl"] > 0).mean() * 100), 2),
        "mean_net_r": round(float(closed["net_r"].mean()), 3),
        "mean_net_pnl": round(float(closed["net_pnl"].mean()), 2),
        "total_net_pnl": round(float(closed["net_pnl"].sum()), 2),
        "status_counts": {k: int(v) for k, v in t["status"].value_counts().items()},
    }


def independent_trades(signals: pd.DataFrame) -> pd.DataFrame:
    """逐信号统计：同一只股票持仓期间不重复开仓，其余不设限制。"""
    rows = []
    for _, g in signals[signals["triggered"]].sort_values("signal_date").groupby("code"):
        busy_until = pd.Timestamp.min
        for _, r in g.iterrows():
            if r["signal_date"] <= busy_until:
                continue
            rows.append(r)
            busy_until = r["exit_date"]
    return pd.DataFrame(rows)


def portfolio(signals: pd.DataFrame, cfg) -> pd.DataFrame:
    """按你实际的做法模拟：每天收盘后按止损距离取前 max-picks 只可选信号挂单。"""
    held: list[dict] = []  # 持仓：exit_date, notional, code
    taken = []
    by_day = signals.sort_values(["signal_date", "stop_pct"]).groupby("signal_date")
    for day, g in by_day:
        # 当天及之前卖掉的仓位，晚上挂单时已经腾出位置和资金
        held = [h for h in held if h["exit_date"] > day]
        free = cfg.max_positions - len(held)
        if free <= 0:
            continue
        held_codes = {h["code"] for h in held}
        cands = g[g["selectable"] & ~g["code"].isin(held_codes)].head(min(free, cfg.max_picks))
        cash_used = sum(h["notional"] for h in held)
        for _, r in cands.iterrows():
            if not r["triggered"]:
                continue  # 没突破，作废，不替补
            notional = r["shares"] * r["entry_price"]
            if cash_used + notional > cfg.account:
                continue
            cash_used += notional
            held.append({"exit_date": r["exit_date"], "notional": notional, "code": r["code"]})
            taken.append(r)
    return pd.DataFrame(taken)


def portfolio_summary(p: pd.DataFrame, cfg) -> dict[str, Any]:
    if p.empty:
        return {"trades": 0}
    closed = p[p["net_pnl"].notna()].sort_values("exit_date")
    daily = closed.groupby("exit_date")["net_pnl"].sum()
    equity = cfg.account + daily.cumsum()
    dd = max_drawdown(pd.concat([pd.Series([cfg.account]), equity.reset_index(drop=True)]))
    years = {}
    for y, g in p.groupby(pd.to_datetime(p["signal_date"]).dt.year):
        gc = g[g["net_pnl"].notna()]
        yd = gc.sort_values("exit_date").groupby("exit_date")["net_pnl"].sum().cumsum()
        years[str(y)] = {
            "trades": int(len(g)),
            "net_pnl": round(float(gc["net_pnl"].sum()), 2),
            "return_pct": round(float(gc["net_pnl"].sum()) / cfg.account * 100, 2),
            "mean_net_r": round(float(gc["net_r"].mean()), 3) if len(gc) else None,
            "max_drawdown": round(max_drawdown(pd.concat([pd.Series([0.0]), yd.reset_index(drop=True)])), 2),
        }
    return {
        "trades": int(len(p)),
        **trade_stats(p),
        "total_return_pct": round(float(closed["net_pnl"].sum()) / cfg.account * 100, 2),
        "max_drawdown_yuan": round(dd, 2),
        "max_drawdown_pct_of_account": round(dd / cfg.account * 100, 2),
        "total_cost": round(float(closed["cost"].sum()), 2),
        "yearly": years,
    }


def holdout_gate(p: pd.DataFrame, cfg) -> dict[str, Any]:
    """预先定死的通过标准，按组合回测判定：
    检验段（holdout-start 之后）每个自然年扣费后平均 R 都 > 0，且整段平均 R >= gate-min-r。
    某一年没有成交也算不通过。调整段只报告，不参与判定。"""
    if cfg.holdout_start is None:
        # 形成期比较不应该伪装成一次样本外检验。显式返回不适用状态，
        # 调用方据此只报告统计数据、不输出策略“通过”的结论。
        return {
            "applicable": False,
            "reason": "形成期模式（--holdout-start none）：未设置样本外检验段，不作通过/不通过判定",
            "passed": None,
        }
    closed = p[p["net_r"].notna()].copy() if not p.empty else pd.DataFrame(columns=["signal_date", "net_r"])
    years_of = pd.to_datetime(closed["signal_date"]).dt.year
    ins = closed[pd.to_datetime(closed["signal_date"]) < cfg.holdout_start]
    oos = closed[pd.to_datetime(closed["signal_date"]) >= cfg.holdout_start]
    need_years = list(range(cfg.holdout_start.year, cfg.end.year + 1))
    by_year = {y: closed.loc[years_of == y, "net_r"] for y in need_years}
    year_ok = {str(y): (len(r) > 0 and float(r.mean()) > 0) for y, r in by_year.items()}
    oos_mean = float(oos["net_r"].mean()) if len(oos) else None
    passed = all(year_ok.values()) and oos_mean is not None and oos_mean >= cfg.gate_min_r
    return {
        "applicable": True,
        "rule": f"{cfg.holdout_start:%Y-%m-%d} 之后每年扣费后平均 R > 0，且整段平均 R >= {cfg.gate_min_r}",
        "in_sample_trades": int(len(ins)),
        "in_sample_mean_net_r": round(float(ins["net_r"].mean()), 3) if len(ins) else None,
        "holdout_trades": int(len(oos)),
        "holdout_mean_net_r": None if oos_mean is None else round(oos_mean, 3),
        "holdout_years": {str(y): {"trades": int(len(r)), "mean_net_r": round(float(r.mean()), 3) if len(r) else None}
                          for y, r in by_year.items()},
        "holdout_year_positive": year_ok,
        "passed": bool(passed),
    }


# ---------------------------------------------------------------- 主程序

def parse_args():
    p = argparse.ArgumentParser(description="腾讯数据源的强势股回调策略日线回测")
    S.add_rule_args(p)
    p.add_argument("--start", type=lambda v: pd.Timestamp(v).normalize(), default=pd.Timestamp("20190101"))
    p.add_argument("--end", type=lambda v: pd.Timestamp(v).normalize(), default=None,
                   help="默认为今天往前 45 天，保证每笔交易都有足够的后续数据")
    p.add_argument("--hold-days", type=int, default=20, help="最大持有交易日（含买入当天）")
    p.add_argument("--max-positions", type=int, default=2, help="组合回测同时最多持仓几只")
    p.add_argument("--holdout-start",
                   type=lambda v: None if str(v).lower() in {"none", "off"} else pd.Timestamp(v).normalize(),
                   default=pd.Timestamp("20250101"),
                   help="检验段起点（预先定死，不要改）；仅形成期比较时填 none，不作通过判定")
    p.add_argument("--gate-min-r", type=float, default=0.2,
                   help="通过门槛（预先定死，不要改）：检验段扣费后平均 R 至少多少")
    p.add_argument("--workers", type=int, default=3, help="下载并发数")
    p.add_argument("--cache-dir", type=Path, default=Path("backtest_cache/tencent_daily"))
    p.add_argument("--output-dir", type=Path, default=Path("backtest_output"))
    p.add_argument("--refresh", action="store_true", help="忽略缓存重新下载")
    p.add_argument("--max-symbols", type=int, help="仅用于快速测试，不能用于正式统计")
    a = p.parse_args()
    S.validate_rule_args(p, a)
    today = pd.Timestamp(date.today())
    if a.end is None:
        a.end = today - pd.Timedelta(days=45)
    if a.start > a.end:
        p.error("--start 不能晚于 --end")
    if a.holdout_start is not None and not a.start < a.holdout_start <= a.end:
        p.error("--holdout-start 必须在 --start 和 --end 之间")
    if a.hold_days < 2 or a.max_positions < 1 or a.workers < 1:
        p.error("--hold-days 至少为 2（T+1），--max-positions 和 --workers 至少为 1")
    return a


def main() -> None:
    cfg = parse_args()
    data_start = cfg.start - pd.Timedelta(days=200)  # 指标预热
    # 为区间末尾的信号留出出场数据，但不超过今天，否则缓存永远判定为不完整
    data_end = min(cfg.end + pd.Timedelta(days=45), pd.Timestamp(date.today()))
    print(f"信号区间：{cfg.start:%Y-%m-%d} 至 {cfg.end:%Y-%m-%d}；日线区间：{data_start:%Y-%m-%d} 至 {data_end:%Y-%m-%d}")
    universe = load_current_main_board()
    print(f"当前主板清单：{len(universe)} 只（已按今天的名称排除 ST/退）")
    histories, failed = collect_histories(universe, cfg, data_start, data_end)
    if not histories:
        print("没有拿到任何日线，检查网络后重试。")
        return
    market_regime = load_market_regime(cfg, data_start, data_end)
    if cfg.market_filter != "none":
        above_days = sum(market_regime.values())
        print(f"市场过滤：{cfg.market_symbol} 收盘 > EMA50 的交易日 {above_days}/{len(market_regime)}")
    print("计算每日 60 日涨幅门槛……")
    thresholds = build_return_thresholds(histories, cfg.top)

    names = universe.set_index("code")["name"].to_dict()
    recs = []
    for n, (code, h) in enumerate(histories.items(), 1):
        recs.extend(backtest_symbol(code, names[code], h, thresholds, market_regime, cfg))
        if n == 1 or n % 500 == 0 or n == len(histories):
            print(f"  回测 {n}/{len(histories)}；累计信号 {len(recs)}", flush=True)

    trade_cols = ["entry_date", "exit_date", "status", "entry_price", "exit_price", "holding_days",
                  "gross_pnl", "cost", "net_pnl", "net_r"]
    signals = pd.DataFrame(recs)
    if signals.empty:
        print("区间内没有任何信号。")
        return
    for c in trade_cols:
        if c not in signals:
            signals[c] = None

    indep = independent_trades(signals)
    port = portfolio(signals, cfg)
    summary = {
        "signal_window": f"{cfg.start:%Y-%m-%d} 至 {cfg.end:%Y-%m-%d}",
        "universe_with_history": len(histories),
        "history_download_failed": len(failed),
        "signals": int(len(signals)),
        "market_filter": "关闭" if cfg.market_filter == "none" else f"{cfg.market_symbol} 收盘 > EMA50",
        "selectable_signals": int(signals["selectable"].sum()),
        "portfolio": portfolio_summary(port, cfg),
        "holdout_gate": holdout_gate(port, cfg),
        "per_signal_reference": trade_stats(indep) if not indep.empty else {"closed_trades": 0},
        "assumptions": {k: (str(v) if isinstance(v, (Path, pd.Timestamp)) else v) for k, v in vars(cfg).items()},
        "known_bias": ["存活偏差：只有当前上市股票", "ST 按今天名称剔除，有未来信息",
                       "未模拟同板块最多 1 只", "日线无法确定盘中先后，同日两者都碰到按止损"],
    }

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    signals.to_csv(cfg.output_dir / f"signals_{stem}.csv", index=False, encoding="utf-8-sig")
    if not port.empty:
        port.to_csv(cfg.output_dir / f"portfolio_trades_{stem}.csv", index=False, encoding="utf-8-sig")
    (cfg.output_dir / f"summary_{stem}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    ps = summary["portfolio"]
    print("\n===== 组合回测（按实际做法，主要看这个）=====")
    if ps.get("closed_trades"):
        print(f"成交 {ps['trades']} 笔，已平仓 {ps['closed_trades']} 笔；扣费后平均 R {ps['mean_net_r']}；"
              f"扣费后赚钱比例 {ps['net_positive_rate_pct']}%")
        print(f"总收益 {ps['total_return_pct']}%（{ps['total_net_pnl']} 元，其中成本 {ps['total_cost']} 元）；"
              f"最大回撤 {ps['max_drawdown_yuan']} 元（账户的 {ps['max_drawdown_pct_of_account']}%）")
        for y, s in ps["yearly"].items():
            print(f"  {y}：{s['trades']} 笔，收益 {s['return_pct']}%，平均 R {s['mean_net_r']}，回撤 {s['max_drawdown']} 元")
    else:
        print("没有平仓交易。")
    ref = summary["per_signal_reference"]
    if ref.get("closed_trades"):
        print(f"\n逐信号参考：{ref['closed_trades']} 笔，扣费后平均 R {ref['mean_net_r']}")
    g = summary["holdout_gate"]
    if not g["applicable"]:
        print("\n===== 形成期统计（不作样本外判定）=====")
        print(g["reason"])
    else:
        print("\n===== 预先定死的检验 =====")
        print(f"规则：{g['rule']}")
        print(f"调整段：{g['in_sample_trades']} 笔，平均 R {g['in_sample_mean_net_r']}（只报告，不参与判定）")
        print(f"检验段：{g['holdout_trades']} 笔，平均 R {g['holdout_mean_net_r']}")
        for y, s in g["holdout_years"].items():
            print(f"  {y}：{s['trades']} 笔，平均 R {s['mean_net_r']}，{'正' if g['holdout_year_positive'][y] else '不为正'}")
        print("结论：" + ("通过。下一步是纸面交易，不是上真钱。" if g["passed"]
                         else "不通过。按事先约定放弃这套策略，不要再改参数重测。"))
    print(f"\n输出目录：{cfg.output_dir}")
    print("注意：存活偏差和 ST 未来信息都会让结果偏好，正收益要打折看。")


if __name__ == "__main__":
    main()

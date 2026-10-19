"""两资产 ETF v1 的前瞻纸面账本工具；绝不向券商发单。

在交易日收盘后运行，例如：
    python paper_two_asset_tracker.py --as-of 20261013          # 仅预览
    python paper_two_asset_tracker.py --as-of 20261013 --commit # 写入虚拟账本

仅在初始化日和每个季度首个共同交易日按实际开盘价调仓。使用未复权价格，自动现金分红
需与券商到账核对；可用 --dividend-cash 手工校正，避免把前复权价格当成真实成交价格。
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import time
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd

import backtest as B


ASSETS = {"510300": "sh510300", "518880": "sh518880"}
DEFAULT_START = pd.Timestamp("20261013")


def new_benchmark(account: float) -> dict[str, Any]:
    """独立的 510300 买入持有参考账户；不与组合争用现金。"""
    return {"code": "510300", "cash": account, "shares": 0, "initialized": False}


def raw_history(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """读取未复权日线：纸面成交和账户估值应使用当天能交易到的实际价格。"""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                raw = ak.stock_zh_a_hist_tx(
                    symbol=symbol,
                    start_date=start.strftime("%Y%m%d"),
                    end_date=end.strftime("%Y%m%d"),
                    adjust="",
                    timeout=20,
                )
            data = B.normalize_history(raw)
            if data is None or data.empty:
                raise RuntimeError(f"{symbol} 未返回有效日线")
            return data
        except Exception as exc:  # 网络数据源短暂失败时有限重试
            last_error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"无法取得 {symbol} 的未复权日线：{last_error}")


def load_panel(as_of: pd.Timestamp) -> pd.DataFrame:
    # 只需最近约一年用来识别季度首个共同交易日；不读取未来日期。
    start = as_of - pd.Timedelta(days=400)
    panel: pd.DataFrame | None = None
    for code, symbol in ASSETS.items():
        hist = raw_history(symbol, start, as_of)
        part = hist[["date", "open", "close", "volume"]].rename(
            columns={"open": f"open_{code}", "close": f"close_{code}", "volume": f"volume_{code}"})
        panel = part if panel is None else panel.merge(part, on="date", how="inner")
    assert panel is not None
    panel = panel.sort_values("date").reset_index(drop=True)
    invalid = [code for code in ASSETS if (panel[f"volume_{code}"] <= 0).any()]
    if invalid:
        raise RuntimeError(f"共同交易日存在零/负成交量，不能建立纸面成交：{','.join(invalid)}")
    return panel


def automatic_dividends(start_exclusive: pd.Timestamp, end_inclusive: pd.Timestamp,
                        holdings: dict[str, int]) -> tuple[list[tuple[pd.Timestamp, str, float]], list[str]]:
    """从 ETF 累计分红表推导每份现金分红增量。

    分红发生在两次纸面运行之间时，持仓在此期间未变，故可按当前（调仓前）份额入账。
    接口失败只给出警告而不阻止账本；使用者可用 --dividend-cash 手动校正。
    """
    records: list[tuple[pd.Timestamp, str, float]] = []
    warnings: list[str] = []
    for code, symbol in ASSETS.items():
        if holdings[code] <= 0:
            continue
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                table = ak.fund_etf_dividend_sina(symbol=symbol)
            if table is None or table.empty:
                continue
            data = table.rename(columns={"日期": "date", "累计分红": "cumulative"})[["date", "cumulative"]].copy()
            data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
            data["cumulative"] = pd.to_numeric(data["cumulative"], errors="coerce")
            data = data.dropna().sort_values("date")
            data["cash_per_share"] = data["cumulative"].diff().fillna(0.0)
            period = data[(data["date"] > start_exclusive) & (data["date"] <= end_inclusive)]
            for row in period.itertuples(index=False):
                if row.cash_per_share > 0:
                    records.append((row.date, code, float(row.cash_per_share) * holdings[code]))
        except Exception as exc:
            warnings.append(f"自动分红数据源失败（{code}）：{exc}；如有实际分红请用 --dividend-cash 手工补记")
    return records, warnings


def commission(amount: float, state: dict[str, Any]) -> float:
    return max(float(state["min_fee"]), amount * float(state["fee_rate"]))


def limited_buy(cash: float, desired: int, price: float, state: dict[str, Any]) -> tuple[int, float]:
    shares = desired // 100 * 100
    while shares >= 100:
        amount = shares * price
        fee = commission(amount, state)
        if amount + fee <= cash + 1e-9:
            return shares, fee
        shares -= 100
    return 0, 0.0


def quarter_first_days(panel: pd.DataFrame) -> set[pd.Timestamp]:
    return set(panel.groupby(panel["date"].dt.to_period("Q"), sort=False).head(1)["date"])


def missed_rebalance_days(panel: pd.DataFrame, last_valuation: pd.Timestamp,
                          as_of: pd.Timestamp) -> list[pd.Timestamp]:
    """返回上次估值后、当前估值日前未执行的季度首日。"""
    return sorted(day for day in quarter_first_days(panel) if last_valuation < day < as_of)


def read_state(path: Path, account: float, start: pd.Timestamp) -> dict[str, Any]:
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        state = {
            "version": "two_asset_etf_v1_paper",
            "paper_start": str(start.date()),
            "account": account,
            "fee_rate": 0.00025,
            "min_fee": 5.0,
            "cash": account,
            "holdings": {code: 0 for code in ASSETS},
            "benchmark": new_benchmark(account),
            "initialized": False,
            "last_valuation_date": None,
        }
    # 仅允许未初始化的旧状态自动补齐基准，防止事后凭空重建已运行账本。
    if "benchmark" not in state:
        if state.get("initialized"):
            raise RuntimeError("已初始化的旧纸面账本缺少基准账户，不能事后重建")
        state["benchmark"] = new_benchmark(float(state.get("account", account)))
    required = {"version", "paper_start", "account", "fee_rate", "min_fee", "cash", "holdings", "initialized"}
    missing = required - state.keys()
    if missing:
        raise RuntimeError(f"纸面状态文件缺少字段：{sorted(missing)}")
    if set(state["holdings"]) != set(ASSETS):
        raise RuntimeError("纸面状态文件的持仓标的不等于冻结规则")
    benchmark = state["benchmark"]
    if (benchmark.get("code") != "510300" or not isinstance(benchmark.get("shares"), int)
            or float(benchmark.get("cash", -1)) < 0 or not isinstance(benchmark.get("initialized"), bool)):
        raise RuntimeError("纸面基准账户无效")
    return state


def make_event(day: pd.Timestamp, event: str, code: str, open_price: float | None,
               close_price: float | None, shares: int, cash: float, commission_paid: float,
               equity: float | None, note: str, amount: float | None = None) -> dict[str, Any]:
    return {
        "date": day.date().isoformat(), "event": event, "code": code,
        "open_price": "" if open_price is None else round(open_price, 4),
        "close_price": "" if close_price is None else round(close_price, 4),
        "shares": shares, "cash": round(cash, 2), "commission": round(commission_paid, 2),
        "equity": "" if equity is None else round(equity, 2),
        "amount": "" if amount is None else round(amount, 2), "note": note,
    }


def execute(day: pd.Timestamp, bar: pd.Series, panel: pd.DataFrame, state: dict[str, Any],
            dividend_cash: float, auto_dividend_records: list[tuple[pd.Timestamp, str, float]] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """按预登记规则在该日开盘进行初始/季度调仓，随后以收盘价标记。"""
    events: list[dict[str, Any]] = []
    cash = float(state["cash"])
    holdings = {code: int(state["holdings"][code]) for code in ASSETS}
    for dividend_day, code, amount in auto_dividend_records or []:
        cash += amount
        events.append(make_event(dividend_day, "DIVIDEND", code, None, None, holdings[code], cash, 0, None,
                                 "新浪累计分红增量自动入账", amount))
    if dividend_cash:
        cash += dividend_cash
        events.append(make_event(day, "DIVIDEND", "CASH", None, None, 0, cash, 0, None,
                                 "用户手工录入的实际现金分红", dividend_cash))

    first_days = quarter_first_days(panel)
    initial_date = pd.Timestamp(state["paper_start"])
    is_initial = not state["initialized"]
    is_quarter_rebalance = day in first_days
    if is_initial and day != initial_date:
        raise RuntimeError(f"纸面账户尚未初始化；只能在冻结起始日 {initial_date:%Y-%m-%d} 建仓，不能事后补录")

    if is_initial or is_quarter_rebalance:
        nav_open = cash + sum(holdings[c] * float(bar[f"open_{c}"]) for c in ASSETS)
        desired = {c: int((nav_open / 2) / float(bar[f"open_{c}"]) // 100 * 100) for c in ASSETS}
        if is_initial and any(desired[c] < 100 for c in ASSETS):
            raise RuntimeError("初始 50% 目标无法买入两只 ETF 的整手，纸面验证不能开始")
        for code in ASSETS:  # 先卖出超配
            excess = max(0, holdings[code] - desired[code])
            if excess < 100:
                continue
            price = float(bar[f"open_{code}"])
            fee = commission(excess * price, state)
            cash += excess * price - fee
            holdings[code] -= excess
            events.append(make_event(day, "SELL", code, price, float(bar[f"close_{code}"]), excess,
                                     cash, fee, None, "季度再平衡", excess * price))
        for code in ASSETS:  # 再买低配，受现金和整手限制
            deficit = max(0, desired[code] - holdings[code])
            if deficit < 100:
                continue
            price = float(bar[f"open_{code}"])
            shares, fee = limited_buy(cash, deficit, price, state)
            if not shares:
                continue
            cash -= shares * price + fee
            holdings[code] += shares
            events.append(make_event(day, "BUY", code, price, float(bar[f"close_{code}"]), shares,
                                     cash, fee, None, "初始建仓" if is_initial else "季度再平衡", shares * price))
        state["initialized"] = True

    equity = cash + sum(holdings[c] * float(bar[f"close_{c}"]) for c in ASSETS)
    events.append(make_event(day, "MARK", "PORTFOLIO", None, None, 0, cash, 0, equity,
                             "收盘估值；未复权价格，分红须手工录入"))
    state["cash"] = round(cash, 2)
    state["holdings"] = holdings
    state["last_valuation_date"] = str(day.date())
    return events, state


def execute_benchmark(day: pd.Timestamp, bar: pd.Series, state: dict[str, Any],
                      auto_dividend_records: list[tuple[pd.Timestamp, str, float]] | None = None,
                      dividend_cash: float = 0.0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """维护独立的 510300 买入持有账户，供期满时与组合公平比较。"""
    events: list[dict[str, Any]] = []
    benchmark = dict(state["benchmark"])
    cash = float(benchmark["cash"])
    shares = int(benchmark["shares"])
    for dividend_day, code, amount in auto_dividend_records or []:
        if code != "510300":
            continue
        cash += amount
        events.append(make_event(dividend_day, "BENCHMARK_DIVIDEND", code, None, None, shares, cash, 0, None,
                                 "510300 买入持有基准：新浪累计分红增量自动入账", amount))
    if dividend_cash:
        cash += dividend_cash
        events.append(make_event(day, "BENCHMARK_DIVIDEND", "CASH", None, None, 0, cash, 0, None,
                                 "510300 买入持有基准：用户手工现金分红校正", dividend_cash))
    if not benchmark["initialized"]:
        price = float(bar["open_510300"])
        desired = int(cash / (price * (1 + float(state["fee_rate"])) ) // 100 * 100)
        if desired < 100:
            raise RuntimeError("基准账户无法买入 510300 的一手")
        fee = commission(desired * price, state)
        cash -= desired * price + fee
        shares += desired
        events.append(make_event(day, "BENCHMARK_BUY", "510300", price, float(bar["close_510300"]), desired,
                                 cash, fee, None, "基准初始买入后持有，不再调仓", desired * price))
        benchmark["initialized"] = True
    equity = cash + shares * float(bar["close_510300"])
    events.append(make_event(day, "BENCHMARK_MARK", "510300", None, None, shares, cash, 0, equity,
                             "510300 买入持有基准收盘估值；未复权价格"))
    benchmark["cash"] = round(cash, 2)
    benchmark["shares"] = shares
    state["benchmark"] = benchmark
    return events, state


def append_events(path: Path, events: list[dict[str, Any]]) -> None:
    headers = ["date", "event", "code", "open_price", "close_price", "shares", "cash", "commission", "equity", "amount", "note"]
    if path.exists() and path.stat().st_size:
        with path.open(newline="", encoding="utf-8") as f:
            old_rows = list(csv.DictReader(f))
        # 账本 v1 早期文件仅少 amount 一列；在首次提交前/后都可无损升级。
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_headers = reader.fieldnames or []
        if existing_headers != headers:
            if set(existing_headers) == set(headers) - {"amount"}:
                with path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(old_rows)
            else:
                raise RuntimeError("纸面账本列结构不受支持，拒绝追加以免损坏记录")
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if write_header:
            writer.writeheader()
        writer.writerows(events)


def write_state(path: Path, state: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def parse_args():
    parser = argparse.ArgumentParser(description="两资产 ETF v1 的前瞻纸面账本；不发送真实订单")
    parser.add_argument("--as-of", type=lambda x: pd.Timestamp(x).normalize(), required=True,
                        help="收盘后运行的交易日，例如 20261013")
    parser.add_argument("--state", type=Path, default=Path("paper_two_asset_v1_state.json"))
    parser.add_argument("--log", type=Path, default=Path("paper_two_asset_v1.csv"))
    parser.add_argument("--account", type=float, default=20_000)
    parser.add_argument("--start", type=lambda x: pd.Timestamp(x).normalize(), default=DEFAULT_START)
    parser.add_argument("--dividend-cash", type=float, default=0.0,
                        help="自动分红之外的当天实际现金调整，用于券商数据校正")
    parser.add_argument("--benchmark-dividend-cash", type=float, default=0.0,
                        help="510300 买入持有基准的手工现金分红校正；不自动等于组合金额")
    parser.add_argument("--no-auto-dividends", action="store_true",
                        help="禁用新浪 ETF 累计分红自动入账；需自行使用 --dividend-cash 记录")
    parser.add_argument("--commit", action="store_true", help="确认写入纸面 CSV/状态；省略时仅预览")
    args = parser.parse_args()
    if args.account <= 0 or args.dividend_cash < 0 or args.benchmark_dividend_cash < 0:
        parser.error("账户金额必须大于 0，分红现金不能为负")
    return args


def main() -> None:
    args = parse_args()
    state = read_state(args.state, args.account, args.start)
    as_of = args.as_of
    start = pd.Timestamp(state["paper_start"])
    if as_of < start:
        print(f"纸面跟踪尚未开始：冻结起始日为 {start:%Y-%m-%d}；未写入任何记录。")
        return
    if state.get("last_valuation_date") is not None and as_of <= pd.Timestamp(state["last_valuation_date"]):
        raise RuntimeError("--as-of 必须晚于纸面状态的最后估值日，防止重复记账")

    panel = load_panel(as_of)
    row = panel[panel["date"] == as_of]
    if row.empty:
        raise RuntimeError("两只 ETF 没有共同的该日行情；请在共同交易日收盘后运行")
    last = (pd.Timestamp(state["last_valuation_date"]).normalize()
            if state.get("last_valuation_date") else start - pd.Timedelta(days=1))
    if state["initialized"] and last < pd.Timestamp(panel.iloc[0]["date"]):
        raise RuntimeError("距上次纸面估值已超过可核验窗口；不得跳过季度调仓或补录历史账本")
    # 只允许在季度首日实际运行调仓；晚到一天会在已知价格上伪造交易，直接使验证失真。
    missed = missed_rebalance_days(panel, last, as_of)
    if state["initialized"] and missed:
        dates = ", ".join(day.strftime("%Y-%m-%d") for day in missed)
        raise RuntimeError(f"错过季度调仓日 {dates}；不得用已知价格补录，纸面验证已失效")
    auto_records, warnings = ([], []) if args.no_auto_dividends else automatic_dividends(last, as_of, state["holdings"])
    benchmark_holdings = {"510300": int(state["benchmark"]["shares"]), "518880": 0}
    benchmark_records, benchmark_warnings = ([], []) if args.no_auto_dividends else automatic_dividends(
        last, as_of, benchmark_holdings)
    for warning in [*warnings, *benchmark_warnings]:
        print(f"警告：{warning}")
    events, next_state = execute(as_of, row.iloc[0], panel, state, args.dividend_cash, auto_records)
    benchmark_events, next_state = execute_benchmark(
        as_of, row.iloc[0], next_state, benchmark_records, args.benchmark_dividend_cash)
    events.extend(benchmark_events)
    portfolio_mark = next(event for event in reversed(events) if event["event"] == "MARK")
    benchmark_mark = next(event for event in reversed(events) if event["event"] == "BENCHMARK_MARK")
    print(f"纸面日期：{as_of:%Y-%m-%d}；组合虚拟净值 {portfolio_mark['equity']} 元；"
          f"现金 {next_state['cash']} 元；持仓 {next_state['holdings']}")
    print(f"510300 买入持有基准：净值 {benchmark_mark['equity']} 元；"
          f"现金 {next_state['benchmark']['cash']} 元；份额 {next_state['benchmark']['shares']}")
    for event in events:
        if event["event"] not in {"MARK", "BENCHMARK_MARK"}:
            print(f"  {event['event']} {event['code']} {event['shares']} 份；佣金 {event['commission']} 元；{event['note']}")
    if args.commit:
        append_events(args.log, events)
        write_state(args.state, next_state)
        print(f"已写入纸面账本：{args.log}；未发送任何真实订单。")
    else:
        print("预览模式：未写入任何文件。确认无误后再加 --commit。")


if __name__ == "__main__":
    main()

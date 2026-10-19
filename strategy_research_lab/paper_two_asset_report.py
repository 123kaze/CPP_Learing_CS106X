"""汇总两资产纸面账本；仅读取 CSV/状态，绝不交易或修改账本。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {"date", "event", "code", "commission", "equity"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="两资产 ETF 纸面组合与 510300 基准报告（只读）")
    parser.add_argument("--log", type=Path, default=Path("paper_two_asset_v1.csv"))
    parser.add_argument("--state", type=Path, default=Path("paper_two_asset_v1_state.json"))
    parser.add_argument("--output", type=Path, help="可选：把报告 JSON 写到此路径；默认只打印")
    return parser.parse_args()


def load_state(path: Path) -> dict[str, Any]:
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state.get("account"), (int, float)) or state["account"] <= 0:
        raise RuntimeError("纸面状态缺少有效初始资金")
    if "paper_start" not in state or "benchmark" not in state:
        raise RuntimeError("纸面状态缺少起始日或 510300 基准账户")
    return state


def load_log(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise RuntimeError(f"找不到纸面账本：{path}")
    data = pd.read_csv(path, dtype={"date": "string", "event": "string", "code": "string"})
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise RuntimeError(f"纸面账本缺少字段：{sorted(missing)}")
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    data["equity"] = pd.to_numeric(data["equity"], errors="coerce")
    data["commission"] = pd.to_numeric(data["commission"], errors="coerce").fillna(0.0)
    if "amount" in data:
        data["amount"] = pd.to_numeric(data["amount"], errors="coerce")
    if data["date"].isna().any():
        raise RuntimeError("纸面账本包含无效日期")
    return data


def marks(data: pd.DataFrame, event: str) -> pd.DataFrame:
    frame = data[data["event"] == event][["date", "equity"]].dropna().sort_values("date").copy()
    if frame["date"].duplicated().any():
        raise RuntimeError(f"{event} 存在重复日终估值")
    return frame


def performance(frame: pd.DataFrame, account: float, paper_start: pd.Timestamp) -> dict[str, Any] | None:
    if frame.empty:
        return None
    equity = pd.concat([pd.Series([account], dtype=float), frame["equity"].reset_index(drop=True)], ignore_index=True)
    running_peak = equity.cummax()
    maximum_drawdown = float((equity / running_peak - 1).min())
    terminal = float(frame.iloc[-1]["equity"])
    end = pd.Timestamp(frame.iloc[-1]["date"])
    years = (end - paper_start).days / 365.25
    cagr = (terminal / account) ** (1 / years) - 1 if years > 0 else None
    return {
        "first_mark": str(pd.Timestamp(frame.iloc[0]["date"]).date()),
        "last_mark": str(end.date()),
        "observed_valuations": int(len(frame)),
        "terminal_equity": round(terminal, 2),
        "total_return_pct": round((terminal / account - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "max_drawdown_pct": round(maximum_drawdown * 100, 2),
    }


def build_report(log_path: Path, state_path: Path) -> dict[str, Any]:
    state = load_state(state_path)
    data = load_log(log_path)
    account = float(state["account"])
    paper_start = pd.Timestamp(state["paper_start"]).normalize()
    portfolio = performance(marks(data, "MARK"), account, paper_start)
    benchmark = performance(marks(data, "BENCHMARK_MARK"), account, paper_start)
    dividend_summary: dict[str, Any]
    if "amount" in data:
        dividend_summary = {
            "portfolio_dividend_cash": round(float(data.loc[data["event"] == "DIVIDEND", "amount"].sum()), 2),
            "benchmark_dividend_cash": round(float(data.loc[data["event"] == "BENCHMARK_DIVIDEND", "amount"].sum()), 2),
        }
    else:
        dividend_summary = {"dividend_cash": "旧账本未单列 amount，无法可靠汇总"}
    report: dict[str, Any] = {
        "paper_start": str(paper_start.date()),
        "initial_account_each": account,
        "portfolio": portfolio,
        "benchmark_510300_buy_and_hold": benchmark,
        "costs_and_cash_dividends": {
            "portfolio_commission": round(float(data.loc[data["event"].isin(["BUY", "SELL"]), "commission"].sum()), 2),
            "benchmark_commission": round(float(data.loc[data["event"] == "BENCHMARK_BUY", "commission"].sum()), 2),
            **dividend_summary,
        },
        "caveats": [
            "报告只统计实际写入的收盘估值；漏掉普通交易日会使最大回撤不完整，必须披露。",
            "只有连续至少 12 个未来季度且未改变规则的记录，才构成前瞻验证证据。",
        ],
    }
    if portfolio is None and benchmark is None:
        report["status"] = "not_started"
        return report
    if portfolio is None or benchmark is None:
        raise RuntimeError("组合与基准的日终估值记录不完整")
    portfolio_dates = set(marks(data, "MARK")["date"])
    benchmark_dates = set(marks(data, "BENCHMARK_MARK")["date"])
    if portfolio_dates != benchmark_dates:
        raise RuntimeError("组合与基准的估值日期不一致")
    report["status"] = "tracking"
    report["portfolio_minus_benchmark_total_return_pct"] = round(
        portfolio["total_return_pct"] - benchmark["total_return_pct"], 2)
    return report


def main() -> None:
    args = parse_args()
    report = build_report(args.log, args.state)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"已写入只读报告：{args.output}")


if __name__ == "__main__":
    main()

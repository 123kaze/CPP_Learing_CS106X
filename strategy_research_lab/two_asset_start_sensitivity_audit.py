"""固定两资产规则的年度起点敏感性审计（不搜索参数）。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

import two_asset_raw_total_return_audit as raw


def parse_args():
    parser = argparse.ArgumentParser(description="两资产 ETF 固定规则的起点敏感性审计")
    parser.add_argument("--end", type=lambda value: pd.Timestamp(value).normalize(), default=pd.Timestamp("20260828"))
    parser.add_argument("--first-start", type=lambda value: pd.Timestamp(value).normalize(), default=pd.Timestamp("20150101"))
    parser.add_argument("--last-start", type=lambda value: pd.Timestamp(value).normalize(), default=pd.Timestamp("20230101"))
    parser.add_argument("--account", type=float, default=20_000)
    parser.add_argument("--fee-rate", type=float, default=0.00025)
    parser.add_argument("--min-fee", type=float, default=5.0)
    parser.add_argument("--output-dir", type=Path, default=Path("results/two_asset_start_sensitivity"))
    cfg = parser.parse_args()
    if not (cfg.first_start <= cfg.last_start < cfg.end) or cfg.account <= 0:
        parser.error("时间或账户参数无效")
    return cfg


def main() -> None:
    args = parse_args()
    data_cfg = SimpleNamespace(end=args.end)
    panel = raw.load_panel(data_cfg)
    dividends = raw.dividend_schedule(args.end)
    rows = []
    for year in range(args.first_start.year, args.last_start.year + 1):
        start = pd.Timestamp(f"{year}0101")
        if start >= args.end:
            continue
        cfg = SimpleNamespace(start=start, end=args.end, account=args.account,
                              fee_rate=args.fee_rate, min_fee=args.min_fee)
        _, _, strategy = raw.simulate(panel, dividends, cfg)
        passive = raw.buy_hold(panel, dividends, cfg)
        rows.append({
            "start": str(start.date()),
            "strategy_terminal_equity": strategy["terminal_equity"],
            "strategy_cagr_pct": strategy["cagr_pct"],
            "strategy_max_drawdown_pct": strategy["max_drawdown_pct"],
            "strategy_total_return_pct": strategy["total_return_pct"],
            "benchmark_cagr_pct": passive["cagr_pct"],
            "benchmark_max_drawdown_pct": passive["max_drawdown_pct"],
            "benchmark_total_return_pct": passive["total_return_pct"],
            "strategy_beats_benchmark_cagr": strategy["cagr_pct"] > passive["cagr_pct"],
        })
    frame = pd.DataFrame(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output_dir / "annual_start_windows.csv", index=False, encoding="utf-8-sig")
    summary = {
        "rule": "510300/518880 各约 50%，季度首日开盘再平衡；未复权价格+现金分红；无参数选择",
        "end": str(args.end.date()), "starts": rows,
        "all_strategy_cagr_positive": bool((frame["strategy_cagr_pct"] > 0).all()),
        "all_strategy_drawdown_better_than_benchmark": bool(
            (frame["strategy_max_drawdown_pct"] >= frame["benchmark_max_drawdown_pct"]).all()),
        "benchmark_cagr_beaten_windows": int(frame["strategy_beats_benchmark_cagr"].sum()),
        "windows": int(len(frame)),
        "caveat": "窗口彼此重叠，且历史数据已被研究过程观察；这是稳健性描述，不是新的独立样本外检验。",
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(frame.to_string(index=False))
    print("\n窗口数：", summary["windows"], "；全部正年化：", summary["all_strategy_cagr_positive"],
          "；全部回撤优于基准：", summary["all_strategy_drawdown_better_than_benchmark"],
          "；年化胜基准窗口：", summary["benchmark_cagr_beaten_windows"])


if __name__ == "__main__":
    main()

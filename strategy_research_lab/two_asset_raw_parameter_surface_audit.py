"""以未复权成交价和现金分红复算预先固定的两资产 3×3 网格。

它是 ``two_asset_parameter_surface_audit.py`` 的独立价格口径审计，而不是选择
历史最高收益参数的工具。所有网格单元都写入输出，无筛选或排序后只展示最佳项。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import two_asset_raw_total_return_audit as raw


WEIGHTS = (0.40, 0.50, 0.60)
FREQUENCIES = ("monthly", "quarterly", "annual")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="两资产 ETF 未复权固定网格审计（非参数选择）")
    parser.add_argument("--start", required=True, type=lambda value: pd.Timestamp(value).normalize())
    parser.add_argument("--end", required=True, type=lambda value: pd.Timestamp(value).normalize())
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
    panel = raw.load_panel(cfg)
    dividends = raw.dividend_schedule(cfg.end)
    rows = []
    for frequency in FREQUENCIES:
        for stock_weight in WEIGHTS:
            _trades, _curve, summary = raw.simulate(
                panel, dividends, cfg, stock_weight=stock_weight, frequency=frequency)
            rows.append(summary)
    table = pd.DataFrame(rows)
    stem = f"{cfg.start:%Y%m%d}_{cfg.end:%Y%m%d}"
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(cfg.output_dir / f"surface_{stem}.csv", index=False, encoding="utf-8-sig")
    result = {
        "hypothesis": "two_asset_etf_raw_fixed_grid_robustness_audit",
        "data": "腾讯未复权日线 + 新浪现金分红",
        "predeclared_grid": {
            "weight_510300": list(WEIGHTS),
            "weight_518880": [round(1 - weight, 2) for weight in WEIGHTS],
            "rebalance_frequency": list(FREQUENCIES),
        },
        "assumptions": {key: (str(value) if isinstance(value, (Path, pd.Timestamp)) else value)
                        for key, value in vars(cfg).items()},
        "results": rows,
        "interpretation": [
            "完整披露预先固定 3×3 网格；不能按年化最高的单元事后选择新策略。",
            "纸面跟踪仍冻结为 510300/518880 各约 50%、季度再平衡。",
            "分红到账日期与券商可能略有差异，且未模拟冲击成本、跟踪误差、申赎与停牌。",
        ],
    }
    (cfg.output_dir / f"summary_{stem}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("===== 两资产 ETF 未复权固定网格审计 =====")
    print(table[["rebalance_frequency", "stock_weight", "cagr_pct", "max_drawdown_pct",
                 "trades", "total_commission", "total_dividend_cash"]].to_string(index=False))
    print(f"输出目录：{cfg.output_dir}")


if __name__ == "__main__":
    main()

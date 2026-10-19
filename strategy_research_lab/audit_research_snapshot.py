"""只读审计研究目录：检查核心脚本副本、关键结果和无效结果标记。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


LAB = Path(__file__).resolve().parent
ROOT = LAB.parent
CORE = ("test.py", "strategy.py", "backtest.py")
VALID_JSON = (
    "results/train_no_filter/summary_20220101_20241231.json",
    "results/train_market_filter/summary_20220101_20241231.json",
    "results/breakout_v1_formation/summary_20220101_20241231.json",
    "results/etf_trend_v1_formation/summary_20140101_20201231.json",
    "results/etf_trend_v1_oos/summary_20210101_20260828.json",
    "results/multi_asset_etf_v1_formation/summary_20150101_20201231.json",
    "results/two_asset_etf_v1_formation/summary_20150101_20201231.json",
    "results/two_asset_etf_v1_exploratory/summary_20210101_20260828.json",
    "results/two_asset_raw_audit_formation/summary_20150101_20201231.json",
    "results/two_asset_raw_audit_exploratory/summary_20210101_20260828.json",
    "results/two_asset_start_sensitivity/summary.json",
    "results/two_asset_grid_formation/summary_20150101_20201231.json",
    "results/two_asset_grid_exploratory/summary_20210101_20260828.json",
    "results/two_asset_raw_grid_formation/summary_20150101_20201231.json",
    "results/two_asset_raw_grid_exploratory/summary_20210101_20260828.json",
)
INVALID_MARKERS = (
    "results/equal_weight_etf_v1_formation/INVALID_DO_NOT_USE.md",
    "results/equal_weight_etf_v1_oos/INVALID_DO_NOT_USE.md",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    problems: list[str] = []
    for name in CORE:
        source, copy = ROOT / name, LAB / name
        if not source.exists() or not copy.exists():
            problems.append(f"缺少核心脚本：{name}")
        elif digest(source) != digest(copy):
            problems.append(f"副本不同步：{name}")
        else:
            print(f"OK  副本一致：{name}")
    for relative in VALID_JSON:
        path = LAB / relative
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("根节点不是 JSON 对象")
            print(f"OK  结果可读：{relative}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            problems.append(f"结果文件无效：{relative}（{exc}）")
    for relative in INVALID_MARKERS:
        path = LAB / relative
        if not path.is_file() or "无效" not in path.read_text(encoding="utf-8"):
            problems.append(f"缺少无效结果标记：{relative}")
        else:
            print(f"OK  无效结果已标记：{relative}")
    state = LAB / "paper_two_asset_v1_state.json"
    try:
        paper = json.loads(state.read_text(encoding="utf-8"))
        benchmark = paper.get("benchmark", {})
        if (paper.get("initialized") is not False or paper.get("last_valuation_date") is not None
                or benchmark.get("code") != "510300" or benchmark.get("initialized") is not False
                or benchmark.get("shares") != 0 or benchmark.get("cash") != paper.get("account")):
            problems.append("纸面账本应在 2026-10-13 前保持未初始化")
        else:
            print("OK  纸面账本尚未初始化")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        problems.append(f"纸面状态文件无效：{exc}")
    ledger = LAB / "paper_two_asset_v1.csv"
    try:
        headers = ledger.read_text(encoding="utf-8").splitlines()[0].split(",")
        if "amount" not in headers or "equity" not in headers:
            problems.append("纸面账本缺少金额或估值列")
        else:
            print("OK  纸面账本具备金额与估值列")
    except (OSError, IndexError) as exc:
        problems.append(f"纸面账本文件无效：{exc}")
    watchdog = LAB / "paper_initialize_watchdog.py"
    if not watchdog.is_file() or "TARGET_DATE" not in watchdog.read_text(encoding="utf-8"):
        problems.append("缺少纸面初始化时间守护")
    else:
        print("OK  纸面初始化守护已就绪")
    if problems:
        print("\n审计失败：")
        print("\n".join(f"- {problem}" for problem in problems))
        raise SystemExit(1)
    print("\n审计通过：研究快照完整；这不等同于策略已获实盘验证。")


if __name__ == "__main__":
    main()

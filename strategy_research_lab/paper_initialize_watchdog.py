"""仅为两资产纸面账户做一次前瞻初始化的 macOS 定时守护。

它绝不调用券商 API。仅在冻结日期 2026-10-13 的 16:00--21:59（上海时区）检查
共同日线；数据存在时才调用纸面跟踪器的 --commit。过期后拒绝补录。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
TARGET_DATE = datetime(2026, 10, 13, tzinfo=ZoneInfo("Asia/Shanghai")).date()
STATE_PATH = ROOT / "paper_two_asset_v1_state.json"
TRACKER_PATH = ROOT / "paper_two_asset_tracker.py"


def now_shanghai() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def read_initialized() -> bool:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return bool(state.get("initialized"))


def eligible(now: datetime) -> bool:
    return now.date() == TARGET_DATE and 16 <= now.hour < 22


def run_once(now: datetime | None = None) -> int:
    now = now or now_shanghai()
    if read_initialized():
        print("纸面账户已初始化；守护不再写入。")
        return 0
    if now.date() < TARGET_DATE:
        print(f"等待冻结建仓日 {TARGET_DATE.isoformat()}；当前 {now.isoformat()}。")
        return 0
    if now.date() > TARGET_DATE:
        print("已错过冻结建仓日；拒绝用之后已知价格补录纸面初始交易。")
        return 1
    if not eligible(now):
        print(f"尚未进入收盘检查窗口；当前 {now.isoformat()}。")
        return 0
    command = [sys.executable, str(TRACKER_PATH), "--as-of", TARGET_DATE.strftime("%Y%m%d"), "--commit"]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="只初始化本地两资产纸面账户；不发送真实订单")
    parser.add_argument("--once", action="store_true", help="执行一次时间门控检查（供 launchd 调用）")
    parser.parse_args()
    raise SystemExit(run_once())


if __name__ == "__main__":
    main()

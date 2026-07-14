#!/usr/bin/env python3
from __future__ import annotations
"""
日志分析器 —— 实验 06 的配套代码。

功能：
  - 统计日志级别分布
  - 提取和统计 IP 地址
  - 统计重复 ERROR 消息
  - 按小时统计日志量
  - 支持过滤

用法：
  python log_analyzer.py app.log
  python log_analyzer.py app.log --level ERROR
  python log_analyzer.py app.log --top 20
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def analyze_log(filepath: Path, level_filter: str | None = None, top_n: int = 10):
    """分析日志文件。"""
    text = filepath.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # --- 统计级别分布 ---
    level_pattern = re.compile(r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b", re.IGNORECASE)
    level_counter = Counter()
    for line in lines:
        # 统一级别名称
        m = level_pattern.search(line)
        if m:
            lvl = m.group(1).upper()
            if lvl == "WARNING":
                lvl = "WARN"
            if lvl == "FATAL":
                lvl = "CRITICAL"
            level_counter[lvl] += 1

    # --- 如果指定了级别过滤，只保留匹配行 ---
    if level_filter:
        filtered_lines = [l for l in lines if level_pattern.search(l) and
                          level_pattern.search(l).group(1).upper() == level_filter.upper()]
    else:
        filtered_lines = lines

    # --- 提取 IP 地址 ---
    ip_pattern = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")
    ip_counter = Counter()
    for line in filtered_lines:
        for ip in ip_pattern.findall(line):
            ip_counter[ip] += 1

    # --- 统计 ERROR 消息 ---
    error_pattern = re.compile(r"\bERROR\b")
    error_msg_counter = Counter()
    for line in filtered_lines:
        if error_pattern.search(line):
            # 提取 ERROR 后面的消息（简化：取 ERROR 之后的部分，去掉时间戳）
            m = re.search(r"ERROR\s*:?\s*(.*)", line, re.IGNORECASE)
            if m:
                msg = m.group(1).strip()
                # 去掉行首可能的时间戳残余
                msg = re.sub(r"^\d{4}-\d{2}-\d{2}\S*\s+", "", msg)
                if len(msg) > 80:
                    msg = msg[:77] + "..."
                error_msg_counter[msg] += 1

    # --- 按小时统计 ---
    hour_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}[ T](\d{2}))")
    hour_counter = Counter()
    for line in filtered_lines:
        m = hour_pattern.search(line)
        if m:
            hour_counter[m.group(2)] += 1

    # --- 输出报告 ---
    print("=" * 60)
    print(f"日志分析报告: {filepath}")
    print("=" * 60)
    print(f"总行数: {len(lines):,}")
    if level_filter:
        print(f"过滤级别: {level_filter}（过滤后 {len(filtered_lines)} 行）")
    print()

    # 级别分布
    if level_counter:
        total = sum(level_counter.values())
        print("--- 日志级别分布 ---")
        for lvl in ["ERROR", "WARN", "INFO", "DEBUG", "CRITICAL"]:
            count = level_counter.get(lvl, 0)
            if count > 0:
                pct = count / total * 100
                bar = "█" * int(pct / 2)
                print(f"  {lvl:<8s}: {count:>6d} ({pct:5.1f}%) {bar}")
        print()

    # 重复 ERROR 消息
    if error_msg_counter:
        print(f"--- 出现最多的 ERROR 消息 (Top {top_n}) ---")
        for i, (msg, count) in enumerate(error_msg_counter.most_common(top_n), 1):
            print(f"  {i:>2}. [{count}次] {msg}")
        print()

    # IP 地址
    if ip_counter:
        print(f"--- IP 地址 Top {top_n} ---")
        for i, (ip, count) in enumerate(ip_counter.most_common(top_n), 1):
            print(f"  {i:>2}. {ip:<18s} ({count} 次)")
        print()

    # 按小时分布
    if hour_counter:
        print(f"--- 按小时分布 ---")
        max_count = max(hour_counter.values())
        for hour in sorted(hour_counter.keys()):
            count = hour_counter[hour]
            bar_len = int(count / max_count * 30)
            bar = "█" * bar_len
            print(f"  {hour}:00  {count:>5d} {bar}")
        print()


def main():
    parser = argparse.ArgumentParser(description="日志分析器")
    parser.add_argument("logfile", help="日志文件路径")
    parser.add_argument("--level", "-l", choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
                        help="只分析指定级别的日志")
    parser.add_argument("--top", "-n", type=int, default=10, help="显示 Top N 条记录（默认 10）")

    args = parser.parse_args()
    filepath = Path(args.logfile)

    if not filepath.exists():
        print(f"错误: 文件不存在: {filepath}")
        sys.exit(1)

    analyze_log(filepath, args.level, args.top)


if __name__ == "__main__":
    main()

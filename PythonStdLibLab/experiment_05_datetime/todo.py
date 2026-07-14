#!/usr/bin/env python3
from __future__ import annotations
"""
命令行 Todo（带截止日期）—— 实验 05 的配套代码。

在实验 04 的基础上添加时间管理功能：
  - 任务支持截止日期 (--due)
  - today / overdue / week 子命令
  - 显示剩余天数

用法：
  python todo.py add "submit homework" --due 2026-07-20
  python todo.py add "buy milk" --due tomorrow
  python todo.py today
  python todo.py overdue
  python todo.py week
"""

import argparse
import calendar
import logging
import re
import sys
from datetime import datetime, date, timedelta

# --- 日志配置 ---


def setup_logging(debug: bool = False):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler("todo.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG if debug else logging.WARNING)
    ch.setFormatter(fmt)
    root.addHandler(ch)


logger = logging.getLogger("todo")

# --- 数据存储（内存） ---
tasks: list[dict] = []
_next_id = 1


def parse_due(due_str: str) -> date:
    """解析截止日期字符串，支持多种格式。"""
    today = date.today()

    # 别名
    aliases = {
        "today": today,
        "tomorrow": today + timedelta(days=1),
        "yesterday": today - timedelta(days=1),
    }
    if due_str.lower() in aliases:
        return aliases[due_str.lower()]

    # "next Monday" / "next Tuesday"
    m = re.match(r"next\s+(\w+)", due_str, re.IGNORECASE)
    if m:
        day_names = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        }
        target = day_names.get(m.group(1).lower())
        if target is not None:
            days_ahead = target - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)

    # N天后: "3d" / "7d"
    m = re.match(r"(\d+)d$", due_str)
    if m:
        return today + timedelta(days=int(m.group(1)))

    # ISO 格式: YYYY-MM-DD
    try:
        return datetime.strptime(due_str, "%Y-%m-%d").date()
    except ValueError:
        pass

    raise ValueError(f"无法解析日期: {due_str}")


def format_due(due_date: date | None) -> str:
    """格式化截止日期显示。"""
    if due_date is None:
        return "无截止日期"

    today = date.today()
    delta = (due_date - today).days

    if delta < 0:
        return f"截止: {due_date} ⚠️ 已过期 {-delta} 天"
    elif delta == 0:
        return f"截止: {due_date} ⚠️ 今天截止!"
    elif delta == 1:
        return f"截止: {due_date} (明天)"
    elif delta <= 7:
        return f"截止: {due_date} (还有 {delta} 天)"
    else:
        return f"截止: {due_date} (还有 {delta} 天)"


def cmd_add(title: str, priority: str = "medium", due: str | None = None):
    global _next_id
    due_date = parse_due(due) if due else None
    task = {
        "id": _next_id,
        "title": title,
        "done": False,
        "priority": priority,
        "due": due_date,
        "created": date.today(),
    }
    tasks.append(task)
    _next_id += 1
    logger.info("添加任务 #%d: %s (截止: %s)", task["id"], task["title"], task["due"])
    due_display = format_due(due_date)
    print(f"添加任务 #{task['id']}: {task['title']} [{task['priority']}]  {due_display}")


def cmd_list(show_done: bool | None = None):
    logger.debug("列出任务 (show_done=%s)", show_done)
    if not tasks:
        print("暂无任务。")
        return

    filtered = tasks
    if show_done is True:
        filtered = [t for t in tasks if t["done"]]
        print("已完成的任务:")
    elif show_done is False:
        filtered = [t for t in tasks if not t["done"]]
        print("待办任务:")
    else:
        print("所有任务:")

    if not filtered:
        print("  (无)")
        return

    for t in filtered:
        status = "✅" if t["done"] else "⬜"
        due = format_due(t.get("due"))
        print(f"  {status} #{t['id']:<4} [{t['priority']:<6}] {t['title']:<20s} {due}")


def cmd_today():
    """显示今天到期的任务。"""
    today = date.today()
    due_today = [t for t in tasks if t.get("due") == today and not t["done"]]
    print(f"今天 ({today}) 到期的任务:")
    if not due_today:
        print("  (无) 今天没有到期的任务！")
        return
    for t in due_today:
        print(f"  ⬜ #{t['id']} [{t['priority']}] {t['title']}")


def cmd_overdue():
    """显示过期的任务。"""
    today = date.today()
    overdue = [t for t in tasks if t.get("due") and t["due"] < today and not t["done"]]
    overdue.sort(key=lambda t: t["due"])
    print("过期未完成的任务:")
    if not overdue:
        print("  (无) 没有过期任务！")
        return
    for t in overdue:
        days = (today - t["due"]).days
        print(f"  ⚠️ #{t['id']} [{t['priority']}] {t['title']} (过期 {days} 天)")


def cmd_week():
    """显示本周任务。"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    this_week = [
        t for t in tasks
        if t.get("due") and week_start <= t["due"] <= week_end and not t["done"]
    ]
    this_week.sort(key=lambda t: t["due"])
    print(f"本周 ({week_start} ~ {week_end}) 任务:")
    if not this_week:
        print("  (无)")
        return
    for t in this_week:
        day_name = t["due"].strftime("%A")
        print(f"  ⬜ #{t['id']} [{t['priority']}] {t['title']} → {t['due']} ({day_name})")


def cmd_done(task_id: int):
    for t in tasks:
        if t["id"] == task_id:
            if t["done"]:
                logger.warning("任务 #%d 已经是完成状态", task_id)
            else:
                t["done"] = True
                logger.info("完成任务 #%d", task_id)
                print(f"完成任务 #{task_id}: {t['title']}")
            return
    logger.error("任务 #%d 不存在", task_id)
    print(f"错误: 任务 #{task_id} 不存在")


def cmd_remove(task_id: int):
    for i, t in enumerate(tasks):
        if t["id"] == task_id:
            removed = tasks.pop(i)
            logger.info("删除任务 #%d", task_id)
            print(f"删除任务 #{task_id}: {removed['title']}")
            return
    logger.error("任务 #%d 不存在", task_id)
    print(f"错误: 任务 #{task_id} 不存在")


def cmd_clear():
    count = len(tasks)
    tasks.clear()
    logger.warning("清空所有任务（共 %d 个）", count)
    print(f"已清空 {count} 个任务")


def main():
    parser = argparse.ArgumentParser(prog="todo", description="命令行任务管理器（带时间管理）")
    parser.add_argument("--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    p_add = subparsers.add_parser("add", help="添加新任务")
    p_add.add_argument("title", help="任务标题")
    p_add.add_argument("--priority", "-p", choices=["high", "medium", "low"], default="medium")
    p_add.add_argument(
        "--due", "-d",
        help="截止日期 (YYYY-MM-DD / today / tomorrow / next Monday / 3d)"
    )

    p_list = subparsers.add_parser("list", help="列出任务")
    p_list.add_argument("--done", action="store_true", default=None, dest="show_done")
    p_list.add_argument("--todo", action="store_false", default=None, dest="show_done")

    p_done = subparsers.add_parser("done", help="标记任务为已完成")
    p_done.add_argument("id", type=int)

    p_remove = subparsers.add_parser("remove", help="删除任务")
    p_remove.add_argument("id", type=int)

    subparsers.add_parser("today", help="显示今天到期的任务")
    subparsers.add_parser("overdue", help="显示过期的任务")
    subparsers.add_parser("week", help="显示本周任务")
    subparsers.add_parser("clear", help="清空所有任务")

    args = parser.parse_args()
    setup_logging(debug=args.debug)

    if args.command is None:
        parser.print_help()
        return

    try:
        if args.command == "add":
            cmd_add(args.title, args.priority, args.due)
        elif args.command == "list":
            cmd_list(show_done=args.show_done)
        elif args.command == "done":
            cmd_done(args.id)
        elif args.command == "remove":
            cmd_remove(args.id)
        elif args.command == "today":
            cmd_today()
        elif args.command == "overdue":
            cmd_overdue()
        elif args.command == "week":
            cmd_week()
        elif args.command == "clear":
            cmd_clear()
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations
"""
Todo CLI —— 命令行任务管理器主入口。

整合了所有实验学到的标准库。

用法:
  todo add "learn Python" --due 2026-07-20 --priority high
  todo list
  todo search python
  todo done 1
  todo remove 1
  todo stats
  todo export tasks.json
  todo import tasks.csv
"""

import argparse
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from . import database as db

logger = logging.getLogger("todo.cli")


# --- 日志配置 ---

def setup_logging(debug: bool = False):
    """配置日志系统。"""
    import logging

    root = logging.getLogger("todo")
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件：所有日志
    log_dir = Path.home() / ".todo"
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / "todo.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # 控制台：WARNING 及以上（debug 模式下全部）
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG if debug else logging.WARNING)
    ch.setFormatter(fmt)
    root.addHandler(ch)


# --- 日期解析 ---

def parse_due(due_str: str) -> str:
    """
    解析截止日期字符串，返回 ISO 格式 (YYYY-MM-DD)。

    支持格式:
      - today / tomorrow
      - next Monday / next Tuesday ...
      - 3d / 7d (N天后)
      - YYYY-MM-DD
    """
    today = date.today()

    aliases = {
        "today": today,
        "tomorrow": today + timedelta(days=1),
    }
    if due_str.lower() in aliases:
        return aliases[due_str.lower()].isoformat()

    # next Weekday
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
            return (today + timedelta(days=days_ahead)).isoformat()

    # Nd
    m = re.match(r"(\d+)d$", due_str)
    if m:
        return (today + timedelta(days=int(m.group(1)))).isoformat()

    # YYYY-MM-DD
    try:
        datetime.strptime(due_str, "%Y-%m-%d")
        return due_str
    except ValueError:
        pass

    raise ValueError(f"无法解析日期: {due_str}")


# --- 命令函数 ---

def cmd_add(args):
    due_date = parse_due(args.due) if args.due else None
    task = db.add_task(args.title, priority=args.priority, due_date=due_date)
    icon = task.status_icon
    due_display = task.due_display
    print(f"{icon} 添加任务 #{task.id}: {task.title} [{task.priority}]  {due_display}")


def cmd_list(args):
    show_done = None
    if args.done:
        show_done = True
    elif args.todo:
        show_done = False

    tasks = db.list_tasks(done_filter=show_done)

    if not tasks:
        print("暂无任务。用 `todo add <标题>` 添加一个吧！")
        return

    header = "所有任务:"
    if show_done is True:
        header = "已完成的任务:"
    elif show_done is False:
        header = "待办任务:"
    print(header)

    for t in tasks:
        print(f"  {t.status_icon} #{t.id:<5} [{t.priority:<6}] {t.title:<25s} {t.due_display}")


def cmd_done(args):
    task = db.get_task(args.id)
    if task is None:
        print(f"错误: 任务 #{args.id} 不存在")
        return
    if task.done:
        print(f"任务 #{args.id} 已经是完成状态")
        return

    db.mark_done(args.id)
    print(f"✅ 完成任务 #{args.id}: {task.title}")


def cmd_remove(args):
    task = db.get_task(args.id)
    if task is None:
        print(f"错误: 任务 #{args.id} 不存在")
        return

    db.delete_task(args.id)
    print(f"删除任务 #{args.id}: {task.title}")


def cmd_edit(args):
    success = db.edit_task(args.id, title=args.title, priority=args.priority)
    if not success:
        print(f"错误: 任务 #{args.id} 不存在")
        return
    task = db.get_task(args.id)
    print(f"编辑任务 #{args.id}: {task.title} [{task.priority}]")


def cmd_search(args):
    tasks = db.search_tasks(args.keyword)
    if not tasks:
        print(f"没有找到包含 \"{args.keyword}\" 的任务")
        return
    print(f"搜索 \"{args.keyword}\" 结果 ({len(tasks)} 条):")
    for t in tasks:
        print(f"  {t.status_icon} #{t.id:<5} [{t.priority:<6}] {t.title}")


def cmd_today(args):
    tasks = db.get_today_tasks()
    print(f"今天 ({date.today()}) 到期的任务:")
    if not tasks:
        print("  (无) 今天没有到期的任务！")
        return
    for t in tasks:
        print(f"  ⬜ #{t.id} [{t.priority}] {t.title}")


def cmd_overdue(args):
    tasks = db.get_overdue_tasks()
    print("过期未完成的任务:")
    if not tasks:
        print("  (无) 没有过期任务！")
        return
    for t in tasks:
        delta = (date.today() - t.due_date).days
        print(f"  ⚠️ #{t.id} [{t.priority}] {t.title} (过期 {delta} 天)")


def cmd_stats(args):
    stats = db.get_stats()
    print("任务统计:")
    print(f"  总计:       {stats['total']:>4}")
    print(f"  已完成:     {stats['done']:>4}")
    print(f"  待办:       {stats['todo']:>4}")
    print(f"  高优先级:   {stats['high_priority']:>4}")
    print(f"  已过期:     {stats['overdue']:>4}")


def cmd_export(args):
    filepath = Path(args.file)
    if filepath.suffix == ".json":
        db.export_json(filepath)
        print(f"导出 {filepath} (JSON 格式) 完成")
    elif filepath.suffix == ".csv":
        db.export_csv(filepath)
        print(f"导出 {filepath} (CSV 格式) 完成")
    else:
        print(f"错误: 不支持的导出格式 \"{filepath.suffix}\"，请用 .json 或 .csv")


def cmd_import(args):
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"错误: 文件不存在: {filepath}")
        return
    if filepath.suffix == ".csv":
        count = db.import_csv(filepath)
        print(f"从 {filepath} 导入了 {count} 条任务")
    else:
        print(f"错误: 不支持导入格式 \"{filepath.suffix}\"，请用 .csv")


def cmd_clear(args):
    db.clear_all()
    print("已清空所有任务")


# --- 主入口 ---

def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="todo",
        description="命令行任务管理器 —— Python 标准库实验课综合项目",
        epilog="数据存储在 ~/.todo/todo.db",
    )
    parser.add_argument("--debug", action="store_true", help="开启 DEBUG 日志")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # add
    p = subparsers.add_parser("add", help="添加新任务")
    p.add_argument("title", help="任务标题")
    p.add_argument("-p", "--priority", choices=["high", "medium", "low"], default="medium")
    p.add_argument("-d", "--due", help="截止日期 (YYYY-MM-DD / today / tomorrow / 3d)")

    # list
    p = subparsers.add_parser("list", help="列出任务")
    p.add_argument("--done", action="store_true", help="只显示已完成")
    p.add_argument("--todo", action="store_true", help="只显示未完成")

    # done
    p = subparsers.add_parser("done", help="标记任务为已完成")
    p.add_argument("id", type=int, help="任务 ID")

    # remove
    p = subparsers.add_parser("remove", help="删除任务")
    p.add_argument("id", type=int, help="任务 ID")

    # edit
    p = subparsers.add_parser("edit", help="编辑任务")
    p.add_argument("id", type=int)
    p.add_argument("title", nargs="?", help="新标题")
    p.add_argument("--priority", "-p", choices=["high", "medium", "low"])

    # search
    p = subparsers.add_parser("search", help="搜索任务")
    p.add_argument("keyword", help="搜索关键词")

    # today
    subparsers.add_parser("today", help="显示今天到期的任务")

    # overdue
    subparsers.add_parser("overdue", help="显示过期任务")

    # stats
    subparsers.add_parser("stats", help="显示统计信息")

    # export
    p = subparsers.add_parser("export", help="导出任务")
    p.add_argument("file", help="输出文件 (.json / .csv)")

    # import
    p = subparsers.add_parser("import", help="导入任务")
    p.add_argument("file", help="输入文件 (.csv)")

    # clear
    subparsers.add_parser("clear", help="清空所有任务")

    args = parser.parse_args(argv)

    # 配置日志
    setup_logging(debug=args.debug)

    # 初始化数据库
    db.init_db()

    if args.command is None:
        parser.print_help()
        return

    # 路由命令
    commands = {
        "add": cmd_add,
        "list": cmd_list,
        "done": cmd_done,
        "remove": cmd_remove,
        "edit": cmd_edit,
        "search": cmd_search,
        "today": cmd_today,
        "overdue": cmd_overdue,
        "stats": cmd_stats,
        "export": cmd_export,
        "import": cmd_import,
        "clear": cmd_clear,
    }

    try:
        commands[args.command](args)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("未预期的错误")
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

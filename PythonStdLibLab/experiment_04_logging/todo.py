#!/usr/bin/env python3
from __future__ import annotations
"""
命令行 Todo（带日志）—— 实验 04 的配套代码。

在实验 03 的基础上添加了完整的 logging 支持：
  - DEBUG → todo_debug.log（所有细节）
  - INFO  → todo.log（正常运行日志）
  - WARNING+ → 控制台（用户可见）

用法：
  python todo.py add "learn logging"
  python todo.py list
  python todo.py done 1
  python todo.py --debug add "debug mode"   # 控制台也显示 DEBUG
"""

import argparse
import logging
import sys

# --- 日志配置 ---


def setup_logging(debug: bool = False):
    """配置日志系统。"""
    # 根 logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # 根 logger 设最低，由 handler 控制级别

    # 格式
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler 1: DEBUG 级别 → 文件（所有细节）
    debug_handler = logging.FileHandler("todo_debug.log", encoding="utf-8")
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(fmt)
    root.addHandler(debug_handler)

    # Handler 2: INFO 级别 → 文件（正常运行日志）
    info_handler = logging.FileHandler("todo.log", encoding="utf-8")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(fmt)
    root.addHandler(info_handler)

    # Handler 3: WARNING 级别 → 控制台（用户可见的问题）
    console_handler = logging.StreamHandler(sys.stderr)
    if debug:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)


# 获取本模块的 logger
logger = logging.getLogger("todo")


# --- 数据存储（内存） ---
tasks: list[dict] = []
_next_id = 1


def cmd_add(title: str, priority: str = "medium"):
    global _next_id
    task = {
        "id": _next_id,
        "title": title,
        "done": False,
        "priority": priority,
    }
    tasks.append(task)
    _next_id += 1
    logger.info("添加任务 #%d: %s [%s]", task["id"], task["title"], task["priority"])
    print(f"添加任务 #{task['id']}: {task['title']} [{task['priority']}]")


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
        print(f"  {status} #{t['id']:<4} [{t['priority']:<6}] {t['title']}")


def cmd_done(task_id: int):
    for t in tasks:
        if t["id"] == task_id:
            if t["done"]:
                logger.warning("任务 #%d 已经是完成状态", task_id)
                print(f"任务 #{task_id} 已经是完成状态")
            else:
                t["done"] = True
                logger.info("完成任务 #%d: %s", task_id, t["title"])
                print(f"完成任务 #{task_id}: {t['title']}")
            return
    logger.error("任务 #%d 不存在", task_id)
    print(f"错误: 任务 #{task_id} 不存在")


def cmd_remove(task_id: int):
    for i, t in enumerate(tasks):
        if t["id"] == task_id:
            removed = tasks.pop(i)
            logger.info("删除任务 #%d: %s", task_id, removed["title"])
            print(f"删除任务 #{task_id}: {removed['title']}")
            return
    logger.error("任务 #%d 不存在", task_id)
    print(f"错误: 任务 #{task_id} 不存在")


def cmd_clear():
    count = len(tasks)
    tasks.clear()
    logger.warning("清空所有任务（共 %d 个）", count)
    print(f"已清空 {count} 个任务")


def cmd_edit(task_id: int, new_title: str):
    for t in tasks:
        if t["id"] == task_id:
            old = t["title"]
            t["title"] = new_title
            logger.info("编辑任务 #%d: \"%s\" -> \"%s\"", task_id, old, new_title)
            print(f"任务 #{task_id}: \"{old}\" -> \"{new_title}\"")
            return
    logger.error("任务 #%d 不存在", task_id)
    print(f"错误: 任务 #{task_id} 不存在")


def main():
    parser = argparse.ArgumentParser(
        prog="todo",
        description="命令行任务管理器（带日志）",
    )
    parser.add_argument(
        "--debug", action="store_true", help="开启 DEBUG 日志输出到控制台"
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    p_add = subparsers.add_parser("add", help="添加新任务")
    p_add.add_argument("title", help="任务标题")
    p_add.add_argument("--priority", "-p", choices=["high", "medium", "low"], default="medium")

    p_list = subparsers.add_parser("list", help="列出任务")
    p_list.add_argument("--done", action="store_true", default=None, dest="show_done")
    p_list.add_argument("--todo", action="store_false", default=None, dest="show_done")

    p_done = subparsers.add_parser("done", help="标记任务为已完成")
    p_done.add_argument("id", type=int)

    p_remove = subparsers.add_parser("remove", help="删除任务")
    p_remove.add_argument("id", type=int)

    p_edit = subparsers.add_parser("edit", help="编辑任务标题")
    p_edit.add_argument("id", type=int)
    p_edit.add_argument("title")

    subparsers.add_parser("clear", help="清空所有任务")

    args = parser.parse_args()

    # 配置日志
    setup_logging(debug=args.debug)

    logger.debug("Todo 启动 (debug=%s)", args.debug)

    if args.command is None:
        parser.print_help()
        return

    if args.command == "add":
        cmd_add(args.title, args.priority)
    elif args.command == "list":
        cmd_list(show_done=args.show_done)
    elif args.command == "done":
        cmd_done(args.id)
    elif args.command == "remove":
        cmd_remove(args.id)
    elif args.command == "edit":
        cmd_edit(args.id, args.title)
    elif args.command == "clear":
        cmd_clear()


if __name__ == "__main__":
    main()

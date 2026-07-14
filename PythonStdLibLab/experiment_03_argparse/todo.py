#!/usr/bin/env python3
from __future__ import annotations
"""
命令行 Todo（内存版）—— 实验 03 的配套代码。

一个最简单的命令行任务管理器，数据存在内存中，程序退出即丢失。
这是 Todo CLI 的第一个版本，后续实验会逐步升级。

用法：
  python todo.py add "learn pathlib"
  python todo.py list
  python todo.py done 1
  python todo.py remove 1
  python todo.py clear
"""

import argparse
import sys

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
    print(f"添加任务 #{task['id']}: {task['title']} [{task['priority']}]")


def cmd_list(show_done: bool | None = None):
    if not tasks:
        print("暂无任务。用 `todo add <标题>` 添加一个吧！")
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
                print(f"任务 #{task_id} 已经是完成状态")
            else:
                t["done"] = True
                print(f"完成任务 #{task_id}: {t['title']}")
            return
    print(f"错误: 任务 #{task_id} 不存在")


def cmd_remove(task_id: int):
    for i, t in enumerate(tasks):
        if t["id"] == task_id:
            removed = tasks.pop(i)
            print(f"删除任务 #{task_id}: {removed['title']}")
            return
    print(f"错误: 任务 #{task_id} 不存在")


def cmd_clear():
    count = len(tasks)
    tasks.clear()
    print(f"已清空 {count} 个任务")


def cmd_edit(task_id: int, new_title: str):
    for t in tasks:
        if t["id"] == task_id:
            old = t["title"]
            t["title"] = new_title
            print(f"任务 #{task_id}: \"{old}\" -> \"{new_title}\"")
            return
    print(f"错误: 任务 #{task_id} 不存在")


def main():
    parser = argparse.ArgumentParser(
        prog="todo",
        description="命令行任务管理器（内存版）",
        epilog="提示: 当前版本数据在退出后丢失。后续实验会加入持久化存储。",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # add
    p_add = subparsers.add_parser("add", help="添加新任务")
    p_add.add_argument("title", help="任务标题")
    p_add.add_argument(
        "--priority", "-p",
        choices=["high", "medium", "low"],
        default="medium",
        help="优先级（默认: medium）",
    )

    # list
    p_list = subparsers.add_parser("list", help="列出任务")
    p_list.add_argument(
        "--done", action="store_true", default=None, dest="show_done", help="只显示已完成"
    )
    p_list.add_argument(
        "--todo", action="store_false", default=None, dest="show_done", help="只显示未完成"
    )
    p_list.add_argument("--all", action="store_true", help="显示所有任务（默认）")
    # 注意: --done 和 --todo 共享 dest="show_done"，会互相覆盖

    # done
    p_done = subparsers.add_parser("done", help="标记任务为已完成")
    p_done.add_argument("id", type=int, help="任务 ID")

    # remove
    p_remove = subparsers.add_parser("remove", help="删除任务")
    p_remove.add_argument("id", type=int, help="任务 ID")

    # edit
    p_edit = subparsers.add_parser("edit", help="编辑任务标题")
    p_edit.add_argument("id", type=int, help="任务 ID")
    p_edit.add_argument("title", help="新标题")

    # clear
    subparsers.add_parser("clear", help="清空所有任务")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # 路由到对应命令
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

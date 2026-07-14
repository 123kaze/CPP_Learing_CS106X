#!/usr/bin/env python3
from __future__ import annotations
"""
命令行 Todo（数据库版）—— 实验 07 的配套代码。

从 JSON 内存版升级到 SQLite 数据库存储：
  - 数据持久化到 todo.db
  - 支持模糊搜索 (search)
  - 支持统计 (stats)
  - 参数化查询防 SQL 注入

用法：
  python todo.py add "learn sqlite3"
  python todo.py list
  python todo.py search sqlite
  python todo.py stats
  python todo.py done 1
"""

import argparse
import logging
import sqlite3
import sys
from datetime import datetime, date, timedelta

logger = logging.getLogger("todo")


def setup_logging(debug: bool = False):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


# --- 数据库操作 ---

DB_PATH = "todo.db"


def get_conn() -> sqlite3.Connection:
    """获取数据库连接。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # 更好的并发支持
    return conn


def init_db():
    """初始化数据库表。"""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
    logger.debug("数据库表已就绪")


# --- 命令实现 ---

def parse_due(due_str: str) -> str | None:
    """解析截止日期，返回 ISO 格式字符串。"""
    import re
    today = date.today()

    aliases = {
        "today": today,
        "tomorrow": today + timedelta(days=1),
    }
    if due_str.lower() in aliases:
        return aliases[due_str.lower()].isoformat()

    m = re.match(r"(\d+)d$", due_str)
    if m:
        return (today + timedelta(days=int(m.group(1)))).isoformat()

    try:
        datetime.strptime(due_str, "%Y-%m-%d")
        return due_str
    except ValueError:
        pass

    raise ValueError(f"无法解析日期: {due_str}")


def cmd_add(title: str, priority: str = "medium", due: str | None = None):
    due_date = parse_due(due) if due else None
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, priority, due_date) VALUES (?, ?, ?)",
            (title, priority, due_date),
        )
        new_id = cur.lastrowid
    logger.info("添加任务 #%d: %s", new_id, title)
    print(f"添加任务 #{new_id}: {title} [{priority}]", end="")
    if due_date:
        print(f"  截止: {due_date}")
    else:
        print()


def cmd_list(show_done: bool | None = None, search: str | None = None):
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list = []

    if show_done is True:
        query += " AND done = 1"
    elif show_done is False:
        query += " AND done = 0"

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY done ASC, priority DESC, id DESC"

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        print("暂无任务。")
        return

    for row in rows:
        status = "✅" if row["done"] else "⬜"
        due_str = ""
        if row["due_date"]:
            due_date = date.fromisoformat(row["due_date"])
            delta = (due_date - date.today()).days
            if delta < 0:
                due_str = f" ⚠️ 过期 {-delta}天"
            elif delta == 0:
                due_str = " ⚠️ 今天截止!"
            elif delta <= 7:
                due_str = f" (还有 {delta}天)"
            else:
                due_str = f" 截止: {row['due_date']}"

        print(f"  {status} #{row['id']:<4} [{row['priority']:<6}] {row['title']:<20s}{due_str}")


def cmd_done(task_id: int):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tasks SET done = 1 WHERE id = ? AND done = 0", (task_id,)
        )
        if cur.rowcount == 0:
            # 检查是否存在
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row and row["done"]:
                print(f"任务 #{task_id} 已经是完成状态")
            else:
                print(f"错误: 任务 #{task_id} 不存在")
        else:
            logger.info("完成任务 #%d", task_id)
            print(f"完成任务 #{task_id}")


def cmd_remove(task_id: int):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            print(f"错误: 任务 #{task_id} 不存在")
        else:
            logger.info("删除任务 #%d", task_id)
            print(f"删除任务 #{task_id}")


def cmd_search(keyword: str):
    """模糊搜索任务标题。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE title LIKE ? ORDER BY id DESC",
            (f"%{keyword}%",),
        ).fetchall()

    if not rows:
        print(f"没有找到包含 \"{keyword}\" 的任务")
        return

    print(f"搜索 \"{keyword}\" 结果 ({len(rows)} 条):")
    for row in rows:
        status = "✅" if row["done"] else "⬜"
        print(f"  {status} #{row['id']:<4} [{row['priority']:<6}] {row['title']}")


def cmd_stats():
    """显示统计信息。"""
    today = date.today().isoformat()
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
        todo_count = total - done
        overdue = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE done = 0 AND due_date IS NOT NULL AND due_date < ?",
            (today,),
        ).fetchone()[0]
        high = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE done = 0 AND priority = 'high'"
        ).fetchone()[0]

    print("任务统计:")
    print(f"  总计:     {total:>4}")
    print(f"  已完成:   {done:>4}")
    print(f"  待办:     {todo_count:>4}")
    print(f"  高优先级: {high:>4}")
    print(f"  已过期:   {overdue:>4}")


def cmd_clear():
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        conn.execute("DELETE FROM tasks")
    print(f"已清空 {count} 个任务")


def cmd_edit(task_id: int, new_title: str):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tasks SET title = ? WHERE id = ?", (new_title, task_id)
        )
        if cur.rowcount == 0:
            print(f"错误: 任务 #{task_id} 不存在")
        else:
            print(f"任务 #{task_id} 已更新")


def cmd_today():
    today = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE done = 0 AND due_date = ?", (today,)
        ).fetchall()
    print(f"今天 ({today}) 到期的任务:")
    if not rows:
        print("  (无)")
        return
    for row in rows:
        print(f"  ⬜ #{row['id']} [{row['priority']}] {row['title']}")


def cmd_overdue():
    today = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE done = 0 AND due_date IS NOT NULL AND due_date < ? ORDER BY due_date",
            (today,),
        ).fetchall()
    print("过期任务:")
    if not rows:
        print("  (无)")
        return
    for row in rows:
        days = (date.today() - date.fromisoformat(row["due_date"])).days
        print(f"  ⚠️ #{row['id']} [{row['priority']}] {row['title']} (过期 {days} 天)")


def main():
    parser = argparse.ArgumentParser(prog="todo", description="命令行任务管理器（SQLite 版）")
    parser.add_argument("--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    p_add = subparsers.add_parser("add", help="添加新任务")
    p_add.add_argument("title", help="任务标题")
    p_add.add_argument("--priority", "-p", choices=["high", "medium", "low"], default="medium")
    p_add.add_argument("--due", "-d", help="截止日期")

    p_list = subparsers.add_parser("list", help="列出任务")
    p_list.add_argument("--done", action="store_true", default=None, dest="show_done")
    p_list.add_argument("--todo", action="store_false", default=None, dest="show_done")

    p_done = subparsers.add_parser("done", help="标记完成")
    p_done.add_argument("id", type=int)

    p_rm = subparsers.add_parser("remove", help="删除任务")
    p_rm.add_argument("id", type=int)

    p_edit = subparsers.add_parser("edit", help="编辑任务")
    p_edit.add_argument("id", type=int)
    p_edit.add_argument("title", help="新标题")

    p_search = subparsers.add_parser("search", help="搜索任务")
    p_search.add_argument("keyword", help="搜索关键词")

    subparsers.add_parser("stats", help="统计信息")
    subparsers.add_parser("today", help="今天到期的任务")
    subparsers.add_parser("overdue", help="过期任务")
    subparsers.add_parser("clear", help="清空所有任务")

    args = parser.parse_args()
    setup_logging(debug=args.debug)

    # 初始化数据库
    init_db()

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
        elif args.command == "edit":
            cmd_edit(args.id, args.title)
        elif args.command == "search":
            cmd_search(args.keyword)
        elif args.command == "stats":
            cmd_stats()
        elif args.command == "today":
            cmd_today()
        elif args.command == "overdue":
            cmd_overdue()
        elif args.command == "clear":
            cmd_clear()
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

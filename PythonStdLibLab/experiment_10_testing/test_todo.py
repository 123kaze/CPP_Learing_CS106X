#!/usr/bin/env python3
"""
Todo 数据库版测试 —— 实验 10 的配套代码。

测试实验 07 (SQLite Todo) 的核心功能。
使用 SQLite 内存数据库，测试不影响真实数据。

运行：
  python -m unittest test_todo.py -v
"""

import sqlite3
import unittest
from datetime import date, timedelta
from typing import Optional, List, Dict, Any


# ============================================================
# 从实验 07 的 todo.py 提取核心函数用于测试
# 实际项目中应该把可测试的逻辑抽取到独立模块
# ============================================================

def create_table(conn: sqlite3.Connection):
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


def add_task(conn: sqlite3.Connection, title: str, priority: str = "medium",
             due_date: str = None) -> int:
    cur = conn.execute(
        "INSERT INTO tasks (title, priority, due_date) VALUES (?, ?, ?)",
        (title, priority, due_date),
    )
    return cur.lastrowid


def get_task(conn: sqlite3.Connection, task_id: int) -> Optional[Dict]:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def mark_done(conn: sqlite3.Connection, task_id: int) -> bool:
    """返回 True 表示成功标记，False 表示不存在或已完成。"""
    cur = conn.execute(
        "UPDATE tasks SET done = 1 WHERE id = ? AND done = 0", (task_id,)
    )
    return cur.rowcount > 0


def delete_task(conn: sqlite3.Connection, task_id: int) -> bool:
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return cur.rowcount > 0


def search_tasks(conn: sqlite3.Connection, keyword: str) -> List[Dict]:
    rows = conn.execute(
        "SELECT * FROM tasks WHERE title LIKE ? ORDER BY id DESC",
        (f"%{keyword}%",),
    ).fetchall()
    return [dict(r) for r in rows]


def count_tasks(conn: sqlite3.Connection, done: Optional[bool] = None) -> int:
    if done is None:
        row = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE done = ?", (1 if done else 0,)
        ).fetchone()
    return row[0]


def parse_due(due_str: str) -> str:
    """解析截止日期字符串。从实验 05 提取。"""
    import re
    today = date.today()
    if due_str.lower() == "today":
        return today.isoformat()
    if due_str.lower() == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    m = re.match(r"(\d+)d$", due_str)
    if m:
        return (today + timedelta(days=int(m.group(1)))).isoformat()
    # 验证 ISO 格式
    from datetime import datetime
    datetime.strptime(due_str, "%Y-%m-%d")
    return due_str


# ============================================================
# 测试
# ============================================================

class TestTodoDatabase(unittest.TestCase):
    """测试 Todo 的数据库操作。"""

    def setUp(self):
        """每个测试前创建内存数据库。"""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        create_table(self.conn)

    def tearDown(self):
        """每个测试后关闭连接。"""
        self.conn.close()

    # --- 添加任务 ---

    def test_add_task_basic(self):
        """添加任务后能读到。"""
        task_id = add_task(self.conn, "test task")
        self.conn.commit()

        task = get_task(self.conn, task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task["title"], "test task")
        self.assertEqual(task["done"], 0)
        self.assertEqual(task["priority"], "medium")

    def test_add_task_with_priority(self):
        """添加带优先级的任务。"""
        task_id = add_task(self.conn, "urgent", priority="high")
        self.conn.commit()

        task = get_task(self.conn, task_id)
        self.assertEqual(task["priority"], "high")

    def test_add_task_with_due_date(self):
        """添加带截止日期的任务。"""
        task_id = add_task(self.conn, "deadline", due_date="2026-07-20")
        self.conn.commit()

        task = get_task(self.conn, task_id)
        self.assertEqual(task["due_date"], "2026-07-20")

    # --- 完成任务 ---

    def test_mark_done(self):
        """完成任务后 done 字段变为 1。"""
        task_id = add_task(self.conn, "to complete")
        self.conn.commit()

        result = mark_done(self.conn, task_id)
        self.conn.commit()

        self.assertTrue(result)
        task = get_task(self.conn, task_id)
        self.assertEqual(task["done"], 1)

    def test_mark_done_twice(self):
        """重复标记同一个任务，第二次应返回 False。"""
        task_id = add_task(self.conn, "to complete")
        self.conn.commit()

        self.assertTrue(mark_done(self.conn, task_id))
        self.conn.commit()
        self.assertFalse(mark_done(self.conn, task_id))

    def test_mark_done_nonexistent(self):
        """完成不存在的任务返回 False。"""
        result = mark_done(self.conn, 999)
        self.assertFalse(result)

    # --- 删除任务 ---

    def test_delete_task(self):
        """删除任务后读不到。"""
        task_id = add_task(self.conn, "to delete")
        self.conn.commit()

        result = delete_task(self.conn, task_id)
        self.conn.commit()

        self.assertTrue(result)
        task = get_task(self.conn, task_id)
        self.assertIsNone(task)

    def test_delete_nonexistent(self):
        """删除不存在的任务返回 False。"""
        result = delete_task(self.conn, 999)
        self.assertFalse(result)

    # --- 搜索 ---

    def test_search_finds_match(self):
        """搜索能找到匹配的任务。"""
        add_task(self.conn, "learn python")
        add_task(self.conn, "learn sqlite")
        add_task(self.conn, "buy milk")
        self.conn.commit()

        results = search_tasks(self.conn, "learn")
        self.assertEqual(len(results), 2)

    def test_search_no_match(self):
        """搜索不到时返回空列表。"""
        add_task(self.conn, "learn python")
        self.conn.commit()

        results = search_tasks(self.conn, "zzznomatch")
        self.assertEqual(len(results), 0)

    def test_search_case_sensitive(self):
        """搜索默认不区分大小写（SQLite LIKE 不区分 ASCII 大小写）。"""
        add_task(self.conn, "Learn Python")
        self.conn.commit()

        results = search_tasks(self.conn, "learn")
        self.assertEqual(len(results), 1)

    # --- 计数 ---

    def test_count_empty(self):
        """空数据库。"""
        self.assertEqual(count_tasks(self.conn), 0)
        self.assertEqual(count_tasks(self.conn, done=False), 0)
        self.assertEqual(count_tasks(self.conn, done=True), 0)

    def test_count_after_add_and_done(self):
        """添加 3 个，完成 1 个后计数正确。"""
        ids = [add_task(self.conn, f"task {i}") for i in range(3)]
        self.conn.commit()
        mark_done(self.conn, ids[0])
        self.conn.commit()

        self.assertEqual(count_tasks(self.conn), 3)
        self.assertEqual(count_tasks(self.conn, done=False), 2)
        self.assertEqual(count_tasks(self.conn, done=True), 1)


class TestParseDue(unittest.TestCase):
    """测试日期解析函数。"""

    def test_today(self):
        result = parse_due("today")
        self.assertEqual(result, date.today().isoformat())

    def test_tomorrow(self):
        result = parse_due("tomorrow")
        expected = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(result, expected)

    def test_n_days(self):
        result = parse_due("7d")
        expected = (date.today() + timedelta(days=7)).isoformat()
        self.assertEqual(result, expected)

    def test_iso_format(self):
        result = parse_due("2026-12-25")
        self.assertEqual(result, "2026-12-25")

    def test_invalid_iso(self):
        with self.assertRaises(ValueError):
            parse_due("2026-13-01")  # 月份不存在


class TestTodoIntegration(unittest.TestCase):
    """集成测试：多步操作。"""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        create_table(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_full_workflow(self):
        """完整工作流：添加 → 列表 → 完成 → 搜索 → 删除。"""
        # 添加 3 个任务
        id1 = add_task(self.conn, "learn python", priority="high")
        id2 = add_task(self.conn, "learn sqlite", priority="medium")
        id3 = add_task(self.conn, "buy milk", priority="low")
        self.conn.commit()

        # 验证初始状态
        self.assertEqual(count_tasks(self.conn), 3)
        self.assertEqual(count_tasks(self.conn, done=False), 3)

        # 完成一个
        self.assertTrue(mark_done(self.conn, id1))
        self.conn.commit()

        # 验证状态变化
        self.assertEqual(count_tasks(self.conn, done=True), 1)
        self.assertEqual(count_tasks(self.conn, done=False), 2)

        # 搜索
        results = search_tasks(self.conn, "learn")
        self.assertEqual(len(results), 2)

        # 删除已完成的任务
        self.assertTrue(delete_task(self.conn, id1))
        self.conn.commit()
        self.assertEqual(count_tasks(self.conn), 2)

        # 删除剩余所有
        delete_task(self.conn, id2)
        delete_task(self.conn, id3)
        self.conn.commit()

        self.assertEqual(count_tasks(self.conn), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

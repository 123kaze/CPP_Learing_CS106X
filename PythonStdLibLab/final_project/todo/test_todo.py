#!/usr/bin/env python3
"""
Todo CLI 测试套件。

运行：
  python -m pytest test_todo.py -v
  或
  python -m unittest test_todo.py -v
"""

import sqlite3
import unittest
import tempfile
import os
from datetime import date, timedelta
from pathlib import Path

# 临时修改数据库路径以使用测试数据库
import todo.database as db

TEST_DB = Path(tempfile.gettempdir()) / "todo_test.db"


class TestDatabase(unittest.TestCase):
    """测试数据库操作。"""

    @classmethod
    def setUpClass(cls):
        """所有测试前：把数据库路径改为临时文件。"""
        cls._orig_db_path = db.DB_PATH
        db.DB_PATH = TEST_DB
        # 确保干净的环境
        if TEST_DB.exists():
            TEST_DB.unlink()
        db.ensure_db_dir()
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        """所有测试后：恢复原始路径并清理。"""
        db.DB_PATH = cls._orig_db_path
        if TEST_DB.exists():
            TEST_DB.unlink()

    def setUp(self):
        """每个测试前清空数据。"""
        with db.get_conn() as conn:
            conn.execute("DELETE FROM tasks")

    # --- 添加任务 ---

    def test_add_task_basic(self):
        task = db.add_task("test task")
        self.assertEqual(task.title, "test task")
        self.assertEqual(task.done, False)
        self.assertEqual(task.priority, "medium")
        self.assertIsNone(task.due_date)

    def test_add_task_with_all_fields(self):
        task = db.add_task("urgent task", priority="high", due_date="2026-12-25")
        self.assertEqual(task.priority, "high")
        self.assertEqual(task.due_date, date(2026, 12, 25))

    # --- 获取任务 ---

    def test_get_task_exists(self):
        created = db.add_task("exists")
        fetched = db.get_task(created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "exists")

    def test_get_task_not_exists(self):
        fetched = db.get_task(99999)
        self.assertIsNone(fetched)

    # --- 列出任务 ---

    def test_list_all(self):
        db.add_task("a")
        db.add_task("b")
        db.add_task("c")
        tasks = db.list_tasks()
        self.assertEqual(len(tasks), 3)

    def test_list_todo_only(self):
        db.add_task("a")
        t = db.add_task("b")
        db.mark_done(t.id)
        tasks = db.list_tasks(done_filter=False)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "a")

    def test_list_done_only(self):
        t = db.add_task("a")
        db.mark_done(t.id)
        db.add_task("b")
        tasks = db.list_tasks(done_filter=True)
        self.assertEqual(len(tasks), 1)
        self.assertTrue(tasks[0].done)

    # --- 完成任务 ---

    def test_mark_done(self):
        task = db.add_task("to do")
        result = db.mark_done(task.id)
        self.assertTrue(result)
        updated = db.get_task(task.id)
        self.assertTrue(updated.done)

    def test_mark_done_twice(self):
        task = db.add_task("to do")
        self.assertTrue(db.mark_done(task.id))
        self.assertFalse(db.mark_done(task.id))

    def test_mark_done_nonexistent(self):
        self.assertFalse(db.mark_done(99999))

    # --- 删除任务 ---

    def test_delete(self):
        task = db.add_task("to delete")
        self.assertTrue(db.delete_task(task.id))
        self.assertIsNone(db.get_task(task.id))

    def test_delete_nonexistent(self):
        self.assertFalse(db.delete_task(99999))

    # --- 编辑任务 ---

    def test_edit_title(self):
        task = db.add_task("old title")
        self.assertTrue(db.edit_task(task.id, title="new title"))
        updated = db.get_task(task.id)
        self.assertEqual(updated.title, "new title")

    # --- 搜索 ---

    def test_search_finds(self):
        db.add_task("learn python")
        db.add_task("learn sqlite")
        db.add_task("buy milk")
        results = db.search_tasks("learn")
        self.assertEqual(len(results), 2)

    def test_search_no_match(self):
        db.add_task("learn python")
        results = db.search_tasks("zzz")
        self.assertEqual(len(results), 0)

    # --- 过期任务 ---

    def test_overdue(self):
        past = (date.today() - timedelta(days=5)).isoformat()
        db.add_task("overdue task", due_date=past)
        results = db.get_overdue_tasks()
        self.assertEqual(len(results), 1)

    # --- 今天任务 ---

    def test_today_tasks(self):
        today = date.today().isoformat()
        db.add_task("today task", due_date=today)
        db.add_task("future task", due_date="2026-12-25")
        results = db.get_today_tasks()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "today task")

    # --- 统计 ---

    def test_stats(self):
        t1 = db.add_task("a", priority="high")
        t2 = db.add_task("b")
        past = (date.today() - timedelta(days=1)).isoformat()
        db.add_task("c", due_date=past)
        db.mark_done(t1.id)

        stats = db.get_stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["done"], 1)
        self.assertEqual(stats["todo"], 2)
        self.assertEqual(stats["overdue"], 1)
        self.assertEqual(stats["high_priority"], 0)  # high 的那个 done 了


class TestTaskModel(unittest.TestCase):
    """测试 Task 数据模型。"""

    def test_is_overdue(self):
        from todo.models import Task
        past = date.today() - timedelta(days=1)
        task = Task(id=1, title="test", due_date=past)
        self.assertTrue(task.is_overdue)

    def test_is_not_overdue_when_done(self):
        from todo.models import Task
        past = date.today() - timedelta(days=1)
        task = Task(id=1, title="test", due_date=past, done=True)
        self.assertFalse(task.is_overdue)

    def test_is_due_today(self):
        from todo.models import Task
        task = Task(id=1, title="test", due_date=date.today())
        self.assertTrue(task.is_due_today)

    def test_days_remaining(self):
        from todo.models import Task
        future = date.today() + timedelta(days=5)
        task = Task(id=1, title="test", due_date=future)
        self.assertEqual(task.days_remaining, 5)

    def test_due_display_overdue(self):
        from todo.models import Task
        past = date.today() - timedelta(days=3)
        task = Task(id=1, title="test", due_date=past)
        self.assertIn("过期", task.due_display)
        self.assertIn("3", task.due_display)


class TestCLIParseDue(unittest.TestCase):
    """测试日期解析（从 cli 模块导入）。"""

    def setUp(self):
        # 为避免导入依赖问题，直接复制 parse_due 逻辑
        from todo.cli import parse_due
        self.parse_due = parse_due

    def test_today(self):
        self.assertEqual(self.parse_due("today"), date.today().isoformat())

    def test_tomorrow(self):
        expected = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(self.parse_due("tomorrow"), expected)

    def test_3d(self):
        expected = (date.today() + timedelta(days=3)).isoformat()
        self.assertEqual(self.parse_due("3d"), expected)

    def test_iso_format(self):
        self.assertEqual(self.parse_due("2026-12-25"), "2026-12-25")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            self.parse_due("not a date")


if __name__ == "__main__":
    unittest.main(verbosity=2)

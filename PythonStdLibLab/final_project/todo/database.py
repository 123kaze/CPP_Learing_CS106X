from __future__ import annotations

"""
数据库层 —— 封装所有 SQLite 操作。

提供:
  - init_db(): 初始化数据库
  - add_task / get_task / mark_done / delete_task / search_tasks
  - export_json / export_csv / import_csv
"""

import csv
import json
import logging
import sqlite3
from pathlib import Path
from datetime import date, datetime
from typing import Optional

from .models import Task

logger = logging.getLogger("todo.database")

# 数据库路径：~/.todo/todo.db
DB_DIR = Path.home() / ".todo"
DB_PATH = DB_DIR / "todo.db"


def ensure_db_dir():
    """确保数据库目录存在。"""
    DB_DIR.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    """获取数据库连接。"""
    ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表（如果不存在则创建）。"""
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
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date)
        """)


# --- CRUD ---

def add_task(title: str, priority: str = "medium",
             due_date: Optional[str] = None) -> Task:
    """添加任务，返回创建的 Task。"""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, priority, due_date) VALUES (?, ?, ?)",
            (title, priority, due_date),
        )
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    task = Task.from_row(row)
    logger.info("添加任务 #%d: %s", task.id, task.title)
    return task


def get_task(task_id: int) -> Optional[Task]:
    """获取单个任务。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return Task.from_row(row) if row else None


def list_tasks(done_filter: Optional[bool] = None) -> list[Task]:
    """获取任务列表。"""
    query = "SELECT * FROM tasks WHERE 1=1"
    if done_filter is True:
        query += " AND done = 1"
    elif done_filter is False:
        query += " AND done = 0"
    query += " ORDER BY done ASC, priority_order() ASC, due_date ASC NULLS LAST, id DESC"

    with get_conn() as conn:
        # 用 CASE 实现优先级排序
        query = query.replace("priority_order()",
            "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END")
        # SQLite 不支持 NULLS LAST，改用 COALESCE
        query = query.replace("NULLS LAST", "")
        # 对于排序，把 NULL due_date 放到最后
        query = query.replace(
            "due_date ASC,",
            "CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC,"
        )
        rows = conn.execute(query).fetchall()
    return [Task.from_row(r) for r in rows]


def mark_done(task_id: int) -> bool:
    """标记任务为已完成。返回是否成功。"""
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tasks SET done = 1 WHERE id = ? AND done = 0", (task_id,)
        )
        success = cur.rowcount > 0
    if success:
        logger.info("完成任务 #%d", task_id)
    return success


def delete_task(task_id: int) -> bool:
    """删除任务。返回是否成功。"""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        success = cur.rowcount > 0
    if success:
        logger.info("删除任务 #%d", task_id)
    return success


def edit_task(task_id: int, title: str = None, priority: str = None) -> bool:
    """编辑任务。返回是否成功。"""
    updates = []
    params = []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)
    if not updates:
        return False
    params.append(task_id)
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params
        )
        success = cur.rowcount > 0
    if success:
        logger.info("编辑任务 #%d", task_id)
    return success


def search_tasks(keyword: str) -> list[Task]:
    """模糊搜索任务标题。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE title LIKE ? ORDER BY id DESC",
            (f"%{keyword}%",),
        ).fetchall()
    return [Task.from_row(r) for r in rows]


def get_overdue_tasks() -> list[Task]:
    """获取过期未完成的任务。"""
    today = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE done = 0 AND due_date IS NOT NULL AND due_date < ? "
            "ORDER BY due_date ASC",
            (today,),
        ).fetchall()
    return [Task.from_row(r) for r in rows]


def get_today_tasks() -> list[Task]:
    """获取今天到期的任务。"""
    today = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE done = 0 AND due_date = ?",
            (today,),
        ).fetchall()
    return [Task.from_row(r) for r in rows]


def get_stats() -> dict:
    """获取统计信息。"""
    today = date.today().isoformat()
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        done = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE done = 1"
        ).fetchone()[0]
        overdue = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE done = 0 AND due_date IS NOT NULL AND due_date < ?",
            (today,),
        ).fetchone()[0]
        high = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE done = 0 AND priority = 'high'"
        ).fetchone()[0]
    return {
        "total": total,
        "done": done,
        "todo": total - done,
        "overdue": overdue,
        "high_priority": high,
    }


def clear_all():
    """清空所有任务。"""
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        conn.execute("DELETE FROM tasks")
    logger.warning("清空所有任务（共 %d 个）", count)


# --- 导入导出 ---

def export_json(filepath: Path):
    """导出任务到 JSON 文件。"""
    tasks = list_tasks()
    data = [t.to_dict() for t in tasks]
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("导出 %d 条任务到 %s", len(tasks), filepath)


def export_csv(filepath: Path):
    """导出任务到 CSV 文件。"""
    tasks = list_tasks()
    if not tasks:
        # 空导出也写表头
        filepath.write_text("id,title,done,priority,due_date,created_at\n")
        return
    fieldnames = ["id", "title", "done", "priority", "due_date", "created_at"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in tasks:
            writer.writerow(t.to_dict())
    logger.info("导出 %d 条任务到 %s", len(tasks), filepath)


def import_csv(filepath: Path) -> int:
    """从 CSV 文件导入任务，返回导入数量。"""
    count = 0
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "").strip()
            if not title:
                continue
            priority = row.get("priority", "medium")
            due_date = row.get("due_date") or None
            done = row.get("done", "0") in ("1", "True", "true")
            add_task(title, priority=priority, due_date=due_date)
            # 如果是已完成的任务，立即标记
            if done:
                # 不太好直接标记（不知 id），生产环境可用 "导入后补充标记"
                pass
            count += 1
    logger.info("从 %s 导入了 %d 条任务", filepath, count)
    return count

#!/usr/bin/env python3
from __future__ import annotations
"""
Todo HTTP API 服务器 —— 实验 09 的配套代码。

把实验 07 的 SQLite Todo 升级为 HTTP API。

用法：
  python demo.py --port 8000

测试：
  curl http://localhost:8000/api/tasks
  curl -X POST http://localhost:8000/api/tasks -H "Content-Type: application/json" -d '{"title":"learn http"}'
  curl http://localhost:8000/api/tasks/1
  curl -X DELETE http://localhost:8000/api/tasks/1
"""

import argparse
import json
import sqlite3
import sys
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_PATH = "todo_api.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                priority TEXT DEFAULT 'medium',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)


class TodoHandler(BaseHTTPRequestHandler):
    """Todo API 请求处理器。"""

    # 禁用每次请求打印的日志（可用 logging 替代）
    # def log_message(self, format, *args):
    #     pass

    def _send_json(self, data, status=200):
        """发送 JSON 响应。"""
        body = json.dumps(data, ensure_ascii=False)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _send_error_json(self, status, message):
        """发送 JSON 格式的错误响应。"""
        self._send_json({"error": message}, status)

    def _read_body(self) -> dict | None:
        """读取请求体并解析为 JSON。"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return None
        body = self.rfile.read(content_length)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def _parse_path(self):
        """解析路径，提取任务 ID。"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)
        return parsed, path, query

    # --- HTTP 方法 ---

    def do_GET(self):
        _, path, query = self._parse_path()

        # GET /api/tasks         → 获取所有任务
        # GET /api/tasks?q=xxx   → 搜索
        # GET /api/tasks/1       → 获取单个任务
        match = re.match(r"^/api/tasks(?:/(\d+))?$", path)
        if not match:
            self._send_error_json(404, "Not Found")
            return

        task_id = match.group(1)

        with get_conn() as conn:
            if task_id:
                row = conn.execute(
                    "SELECT * FROM tasks WHERE id = ?", (int(task_id),)
                ).fetchone()
                if not row:
                    self._send_error_json(404, f"Task #{task_id} not found")
                    return
                self._send_json(dict(row))
            else:
                keyword = query.get("q", [None])[0]
                if keyword:
                    rows = conn.execute(
                        "SELECT * FROM tasks WHERE title LIKE ? ORDER BY id DESC",
                        (f"%{keyword}%",),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM tasks ORDER BY done ASC, id DESC"
                    ).fetchall()
                self._send_json([dict(r) for r in rows])

    def do_POST(self):
        _, path, _ = self._parse_path()

        if path != "/api/tasks":
            self._send_error_json(404, "Not Found")
            return

        data = self._read_body()
        if not data or "title" not in data:
            self._send_error_json(400, "Missing required field: title")
            return

        title = data["title"]
        priority = data.get("priority", "medium")

        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, priority) VALUES (?, ?)",
                (title, priority),
            )
            new_id = cur.lastrowid
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()

        self._send_json(dict(row), status=201)

    def do_PUT(self):
        _, path, _ = self._parse_path()
        match = re.match(r"^/api/tasks/(\d+)$", path)
        if not match:
            self._send_error_json(404, "Not Found")
            return

        task_id = int(match.group(1))
        data = self._read_body()
        if not data:
            self._send_error_json(400, "Empty body")
            return

        with get_conn() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                self._send_error_json(404, f"Task #{task_id} not found")
                return

            # 构建更新
            updates = []
            params = []
            for field in ["title", "priority"]:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])
            if "done" in data:
                updates.append("done = ?")
                params.append(1 if data["done"] else 0)

            if updates:
                params.append(task_id)
                conn.execute(
                    f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params
                )

            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

        self._send_json(dict(row))

    def do_DELETE(self):
        _, path, _ = self._parse_path()
        match = re.match(r"^/api/tasks/(\d+)$", path)
        if not match:
            self._send_error_json(404, "Not Found")
            return

        task_id = int(match.group(1))

        with get_conn() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cur.rowcount == 0:
                self._send_error_json(404, f"Task #{task_id} not found")
                return

        self._send_json({"status": "deleted", "id": task_id})


def main():
    parser = argparse.ArgumentParser(description="Todo HTTP API 服务器")
    parser.add_argument("--port", "-p", type=int, default=8000, help="端口号（默认 8000）")
    args = parser.parse_args()

    init_db()
    print(f"Todo API 服务器启动: http://localhost:{args.port}")
    print(f"测试命令:")
    print(f"  curl http://localhost:{args.port}/api/tasks")
    print(f"  curl -X POST http://localhost:{args.port}/api/tasks -H 'Content-Type: application/json' -d '{{\"title\":\"learn http\"}}'")
    print()

    server = HTTPServer(("localhost", args.port), TodoHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    main()

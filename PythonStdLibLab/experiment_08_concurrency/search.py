#!/usr/bin/env python3
from __future__ import annotations
"""
多线程文件搜索器 —— 实验 08 的配套代码。

提供三种模式：
  - serial：串行搜索（基准对比）
  - pool：使用 ThreadPoolExecutor.map（推荐入门）
  - queue：生产者-消费者模式（进阶）

用法：
  python search.py ./ keyword
  python search.py ./ keyword --workers 8
  python search.py ./ keyword --mode pool
  python search.py ./ keyword --glob "*.py"
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Queue
from threading import Thread


def find_files(root: Path, pattern: str = "*") -> list[Path]:
    """递归查找所有匹配的文件。"""
    files = [f for f in root.rglob(pattern) if f.is_file()]
    return files


def search_file(filepath: Path, keyword: str) -> tuple[Path, int, str | None]:
    """
    在单个文件中搜索关键词。
    返回: (文件路径, 匹配行数, 第一条匹配行内容或 None)
    """
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return (filepath, 0, None)

    if keyword not in content:
        return (filepath, 0, None)

    # 统计匹配行
    lines = content.splitlines()
    match_lines = [l for l in lines if keyword in l]
    first_match = match_lines[0].strip() if match_lines else None

    return (filepath, len(match_lines), first_match)


# --- 模式 1: 串行 ---

def search_serial(files: list[Path], keyword: str) -> list[tuple]:
    """串行搜索（用作基准对比）。"""
    results = []
    for f in files:
        path, count, first = search_file(f, keyword)
        if count > 0:
            results.append((path, count, first))
    return results


# --- 模式 2: ThreadPoolExecutor ---

def search_pool(files: list[Path], keyword: str, max_workers: int = 4) -> list[tuple]:
    """使用线程池搜索。"""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # map 方式：按提交顺序返回
        futures = executor.map(
            lambda f: search_file(f, keyword), files
        )
        for path, count, first in futures:
            if count > 0:
                results.append((path, count, first))

    return results


# --- 模式 3: 生产者-消费者 ---

def search_queue(files: list[Path], keyword: str, max_workers: int = 4) -> list[tuple]:
    """
    生产者-消费者模式：
    - 主线程作为生产者，把文件路径放入队列
    - N 个 worker 线程从队列取文件并搜索
    """
    results: list[tuple] = []
    results_lock = __import__("threading").Lock()

    q: Queue = Queue()

    def worker():
        while True:
            filepath = q.get()
            if filepath is None:  # 毒丸：退出信号
                q.task_done()
                break

            path, count, first = search_file(filepath, keyword)
            if count > 0:
                with results_lock:
                    results.append((path, count, first))
            q.task_done()

    # 启动 worker 线程
    threads = []
    for i in range(max_workers):
        t = Thread(target=worker, name=f"Worker-{i}", daemon=True)
        t.start()
        threads.append(t)

    # 生产者：放入所有文件
    for f in files:
        q.put(f)

    # 等待所有任务完成
    q.join()

    # 发送退出信号
    for _ in threads:
        q.put(None)

    # 等待所有 worker 退出
    for t in threads:
        t.join()

    return results


# --- 模式 4: as_completed（实时输出）---

def search_pool_realtime(files: list[Path], keyword: str, max_workers: int = 4) -> list[tuple]:
    """使用 submit + as_completed，找到即输出。"""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(search_file, f, keyword): f for f in files}
        for future in as_completed(futures):
            path, count, first = future.result()
            if count > 0:
                results.append((path, count, first))
                print(f"  🔍 {path} ({count} 处匹配)")

    return results


def main():
    parser = argparse.ArgumentParser(description="多线程文件搜索器")
    parser.add_argument("directory", help="搜索目录")
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument("--workers", "-w", type=int, default=4, help="线程数（默认 4）")
    parser.add_argument(
        "--mode", "-m",
        choices=["serial", "pool", "queue", "realtime"],
        default="pool",
        help="搜索模式: serial(串行) pool(线程池) queue(生产者消费者) realtime(实时输出)",
    )
    parser.add_argument("--glob", "-g", default="*", help="文件名模式（如 *.py）")
    parser.add_argument("--output", "-o", help="输出结果到文件")

    args = parser.parse_args()
    root = Path(args.directory)

    if not root.exists() or not root.is_dir():
        print(f"错误: 目录不存在: {root}")
        sys.exit(1)

    # 1. 扫描文件
    print(f"扫描文件: {root} (模式: {args.glob})")
    t0 = time.perf_counter()
    files = find_files(root, args.glob)
    scan_time = time.perf_counter() - t0
    print(f"找到 {len(files)} 个文件 (耗时 {scan_time:.2f}s)")

    if not files:
        print("没有文件可搜索。")
        return

    # 2. 搜索
    keyword = args.keyword
    print(f"搜索关键词: \"{keyword}\" (模式: {args.mode}, 线程: {args.workers})")

    t0 = time.perf_counter()

    if args.mode == "serial":
        results = search_serial(files, keyword)
    elif args.mode == "pool":
        results = search_pool(files, keyword, args.workers)
    elif args.mode == "queue":
        results = search_queue(files, keyword, args.workers)
    elif args.mode == "realtime":
        results = search_pool_realtime(files, keyword, args.workers)
    else:
        results = []

    search_time = time.perf_counter() - t0

    # 3. 输出结果
    print(f"\n{'='*60}")
    print(f"搜索完成: 找到 {len(results)} 个包含 \"{keyword}\" 的文件")
    print(f"扫描耗时: {scan_time:.2f}s, 搜索耗时: {search_time:.2f}s")
    print(f"{'='*60}")

    for path, count, first in results:
        print(f"\n📄 {path} ({count} 处匹配)")
        if first:
            preview = first[:120] + "..." if len(first) > 120 else first
            print(f"   {preview}")

    # 输出到文件
    if args.output:
        out_path = Path(args.output)
        with out_path.open("w", encoding="utf-8") as f:
            f.write(f"搜索关键词: {keyword}\n")
            f.write(f"搜索目录: {root}\n")
            f.write(f"匹配文件数: {len(results)}\n")
            f.write(f"{'='*60}\n")
            for path, count, _ in results:
                f.write(f"{path}\t{count} 处匹配\n")
        print(f"\n结果已保存到: {out_path}")


if __name__ == "__main__":
    main()

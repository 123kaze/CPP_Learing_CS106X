#!/usr/bin/env python3
from __future__ import annotations
"""
文件分类器 —— 实验 01 的配套代码。

功能：
  1. 递归扫描目录，统计每种后缀的文件数量
  2. 支持按后缀分类复制/移动到目标目录
  3. 支持过滤特定后缀

用法：
  python file_classifier.py /path/to/folder
  python file_classifier.py /path/to/folder --copy-to ./sorted
  python file_classifier.py /path/to/folder --ext .py .cpp
"""

import argparse
import shutil
from pathlib import Path
from collections import defaultdict


def scan_directory(root: Path, extensions: list[str] | None = None):
    """
    递归扫描目录，统计每种后缀的文件。

    返回:
      dict: {后缀: [Path列表]}
    """
    by_ext = defaultdict(list)

    for f in root.rglob("*"):
        if not f.is_file():
            continue
        ext = f.suffix.lower() or "(无后缀)"
        if extensions and ext not in extensions:
            continue
        by_ext[ext].append(f)

    return dict(by_ext)


def print_stats(by_ext: dict):
    """打印统计信息。"""
    print(f"\n{'后缀':<15} {'数量':<8} {'总大小':<12}")
    print("-" * 40)

    total_files = 0
    total_size = 0
    for ext in sorted(by_ext.keys()):
        files = by_ext[ext]
        size = sum(f.stat().st_size for f in files)
        print(f"{ext:<15} {len(files):<8} {format_size(size):<12}")
        total_files += len(files)
        total_size += size

    print("-" * 40)
    print(f"{'总计':<15} {total_files:<8} {format_size(total_size):<12}")

    # 最大的 5 个文件
    all_files = [f for files in by_ext.values() for f in files]
    all_files.sort(key=lambda f: f.stat().st_size, reverse=True)
    if all_files:
        print(f"\n最大的 5 个文件:")
        for f in all_files[:5]:
            print(f"  {format_size(f.stat().st_size):>10s}  {f}")


def classify_copy(by_ext: dict, dest: Path, *, move: bool = False):
    """
    按后缀分类，复制或移动文件到目标目录。
    目标目录结构：dest/{ext_name}/file
    """
    for ext, files in by_ext.items():
        # 清理后缀名用作目录名（去掉开头的点）
        dir_name = ext.lstrip(".") if ext != "(无后缀)" else "no_extension"
        target_dir = dest / dir_name
        target_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            target = target_dir / f.name
            if move:
                print(f"移动: {f} -> {target}")
                shutil.move(str(f), str(target))
            else:
                print(f"复制: {f} -> {target}")
                shutil.copy2(str(f), str(target))


def format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def main():
    parser = argparse.ArgumentParser(description="文件分类器 —— 按后缀统计和分类文件")
    parser.add_argument("folder", type=str, help="要扫描的目录路径")
    parser.add_argument(
        "--copy-to", type=str, default=None, help="按后缀分类复制到目标目录"
    )
    parser.add_argument(
        "--move-to", type=str, default=None, help="按后缀分类移动到目标目录"
    )
    parser.add_argument(
        "--ext", nargs="*", default=None,
        help="只统计指定后缀（如 --ext .py .cpp）"
    )

    args = parser.parse_args()
    root = Path(args.folder)

    if not root.exists():
        print(f"错误: 路径不存在 —— {root}")
        return
    if not root.is_dir():
        print(f"错误: 不是目录 —— {root}")
        return

    # 如果传入了 --ext，确保后缀都以 "." 开头
    extensions = None
    if args.ext:
        extensions = [e if e.startswith(".") else f".{e}" for e in args.ext]
        # 也支持全大写/小写匹配
        extensions = [e.lower() for e in extensions]

    print(f"扫描目录: {root}")
    by_ext = scan_directory(root, extensions)
    print_stats(by_ext)

    if args.copy_to:
        dest = Path(args.copy_to)
        classify_copy(by_ext, dest, move=False)
        print(f"\n分类复制完成: {dest}")

    if args.move_to:
        dest = Path(args.move_to)
        classify_copy(by_ext, dest, move=True)
        print(f"\n分类移动完成: {dest}")


if __name__ == "__main__":
    main()

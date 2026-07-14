#!/usr/bin/env python3
from __future__ import annotations
"""
格式转换器 —— 实验 02 的配套代码。

功能：
  - CSV ↔ JSON 双向转换
  - 从 config.ini 读取配置
  - 自动检测输入格式

用法：
  python convert.py students.csv --to json --output students.json
  python convert.py students.json --to csv --output students.csv
  python convert.py --config config.ini
"""

import argparse
import configparser
import csv
import json
import sys
from pathlib import Path


def detect_format(filepath: Path) -> str:
    """根据后缀检测文件格式。"""
    ext = filepath.suffix.lower()
    if ext == ".csv":
        return "csv"
    elif ext == ".json":
        return "json"
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def read_csv(filepath: Path) -> list[dict]:
    """读取 CSV 文件，返回字典列表。"""
    rows = []
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def read_json(filepath: Path) -> list[dict]:
    """读取 JSON 文件，返回列表（如果 JSON 是对象则包装成单元素列表）。"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    else:
        return [data]


def write_csv(data: list[dict], filepath: Path):
    """将字典列表写入 CSV。"""
    if not data:
        print("警告: 数据为空，生成空 CSV")
        return
    fieldnames = list(data[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def write_json(data: list[dict], filepath: Path, pretty: bool = True):
    """将字典列表写入 JSON。"""
    kwargs = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, **kwargs)


def convert(input_path: Path, output_path: Path, to_format: str):
    """执行格式转换。"""
    input_format = detect_format(input_path)

    if input_format == to_format:
        print(f"输入和输出格式相同，直接复制")
        output_path.write_bytes(input_path.read_bytes())
        return

    # 读取
    print(f"读取: {input_path} (格式: {input_format})")
    if input_format == "csv":
        data = read_csv(input_path)
    else:
        data = read_json(input_path)

    print(f"读取到 {len(data)} 条记录")

    # 写入
    if to_format == "csv":
        write_csv(data, output_path)
    else:
        write_json(data, output_path)

    print(f"写入: {output_path} (格式: {to_format})")


def main():
    parser = argparse.ArgumentParser(description="格式转换器 —— CSV ↔ JSON")
    parser.add_argument("input", nargs="?", help="输入文件路径")
    parser.add_argument("--to", choices=["csv", "json"], help="目标格式")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--config", "-c", help="从配置文件读取参数")
    parser.add_argument("--no-pretty", action="store_true", help="JSON 不格式化")

    args = parser.parse_args()

    # 从配置文件读取
    if args.config:
        config = configparser.ConfigParser()
        config.read(args.config, encoding="utf-8")
        input_path = Path(config.get("io", "input", fallback=None) or "")
        to_format = config.get("io", "format", fallback=None)
        output_path = Path(config.get("io", "output", fallback=None) or "")
        if not input_path.exists():
            print(f"错误: 配置文件中指定的输入路径不存在: {input_path}")
            sys.exit(1)
    else:
        if not args.input or not args.to or not args.output:
            parser.print_help()
            print("\n示例:")
            print("  python convert.py data.csv --to json -o data.json")
            print("  python convert.py data.json --to csv -o data.csv")
            print("  python convert.py --config config.ini")
            sys.exit(1)
        input_path = Path(args.input)
        to_format = args.to
        output_path = Path(args.output)

    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    try:
        convert(input_path, output_path, to_format)
        print("完成!")
    except Exception as e:
        print(f"转换失败: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

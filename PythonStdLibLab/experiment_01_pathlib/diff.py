"""
比较 file_classifier.py 和 fileclu.py 的差异。

用法：
  python diff.py                  # 终端输出差异
  python diff.py --html           # 生成 HTML 差异报告
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

HERE = Path(__file__).parent
FILE_A = HERE / "file_classifier.py"
FILE_B = HERE / "fileclu.py"


def read_lines(path: Path) -> list[str]:
    """读取文件，返回行列表（含换行符）。"""
    with open(path, encoding="utf-8") as f:
        return f.readlines()


def show_unified_diff(a_lines: list[str], b_lines: list[str],
                      name_a: str, name_b: str):
    """显示 unified diff 格式（类似 git diff）。"""
    diff = difflib.unified_diff(
        a_lines, b_lines,
        fromfile=name_a, tofile=name_b,
        lineterm="",
    )
    print("=" * 60)
    print("Unified Diff (git diff 风格)")
    print("=" * 60)
    for line in diff:
        print(line)


def show_context_diff(a_lines: list[str], b_lines: list[str],
                      name_a: str, name_b: str):
    """显示 context diff 格式（带上下文）。"""
    diff = difflib.context_diff(
        a_lines, b_lines,
        fromfile=name_a, tofile=name_b,
        lineterm="",
    )
    print("\n" + "=" * 60)
    print("Context Diff")
    print("=" * 60)
    for line in diff:
        print(line)


def show_side_by_side(a_lines: list[str], b_lines: list[str],
                      name_a: str, name_b: str):
    """逐行比较，按 Differ 标记差异（+ - ? 标记）。"""
    differ = difflib.Differ()
    result = list(differ.compare(a_lines, b_lines))

    print("\n" + "=" * 60)
    print("Differ 逐行比较")
    print("=" * 60)
    print(f"  标记:  - {name_a}")
    print(f"          + {name_b}")
    print(f"          ? 差异位置")
    print("-" * 60)

    for line in result:
        print(line, end="")


def show_summary(a_lines: list[str], b_lines: list[str]):
    """显示差异统计摘要。"""
    matcher = difflib.SequenceMatcher(None, a_lines, b_lines)
    print("\n" + "=" * 60)
    print("差异统计")
    print("=" * 60)
    print(f"  {FILE_A.name}: {len(a_lines)} 行")
    print(f"  {FILE_B.name}: {len(b_lines)} 行")
    print(f"  相似度: {matcher.ratio():.1%}")

    # 按 opcode 分类统计
    stats = {"equal": 0, "replace": 0, "delete": 0, "insert": 0}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            stats["equal"] += i2 - i1
        elif tag == "replace":
            stats["replace"] += max(i2 - i1, j2 - j1)
        elif tag == "delete":
            stats["delete"] += i2 - i1
        elif tag == "insert":
            stats["insert"] += j2 - j1

    for label, count in stats.items():
        name_map = {"equal": "相同", "replace": "替换", "delete": "删除", "insert": "新增"}
        print(f"  {name_map[label]}: {count} 行")


def generate_html(a_lines: list[str], b_lines: list[str],
                  name_a: str, name_b: str):
    diff = difflib.HtmlDiff()
    html = diff.make_file(
        a_lines, b_lines,
        fromdesc=name_a, todesc=name_b,
        context=True, numlines=2,
    )
    output_path = HERE / "diff_report.html"
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)


def main():
    a = read_lines(FILE_A)
    b = read_lines(FILE_B)

    if "--html" in sys.argv:
        path = generate_html(a, b, FILE_A.name, FILE_B.name)
        print(f"HTML 报告已生成: {path}")
        return

    show_summary(a, b)
    show_unified_diff(a, b, FILE_A.name, FILE_B.name)
    show_context_diff(a, b, FILE_A.name, FILE_B.name)
    show_side_by_side(a, b, FILE_A.name, FILE_B.name)


if __name__ == "__main__":
    main()

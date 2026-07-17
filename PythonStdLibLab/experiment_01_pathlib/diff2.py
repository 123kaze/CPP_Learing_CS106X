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
from unittest import result

from cryptography.x509 import name

HERE = Path(__file__).parent
FILE_A = HERE / "file_classifier.py"
FILE_B = HERE / "fileclu.py"
print(FILE_A.as_posix())
print(FILE_B)
def read_lines(path:Path) -> list[str]:
    '''
    读取文件
    :param path:
    :return:
    '''
    with open(path.as_posix(), encoding='utf-8') as f:
        return f.readlines()

def show_unified_diff(a_lines: list[str], b_lines: list[str],
                      name_a:str,name_b:str):
    '''
    显示diff ，类似git diff风格
    :param a_lines:
    :param b_lines:
    :param name_a:
    :param name_b:
    :return:
    '''
    diff = difflib.unified_diff(a_lines, b_lines,
                                fromfile=name_a, tofile=name_b,
                                lineterm="")
    print("=" * 60)
    print("Unified Diff (git diff 风格)")
    print("=" * 60)
    for line in diff:
        print(line)

def show_context_diff(a_lines: list[str], b_lines: list[str],
                      name_a:str,name_b:str):
    '''
    显示context diff 格式
    :param a_lines:
    :param b_lines:
    :param name_a:
    :param name_b:
    :return:
    '''
    diff = difflib.context_diff(a_lines, b_lines,
                                fromfile=name_a, tofile=name_b,
                                lineterm="")
    print("\n" + "=" * 60)
    print("context Diff")
    print("=" * 60)
    for line in diff:
        print(line)

def show_side_by_side(a_lines: list[str], b_lines: list[str],
                      name_a:str,name_b:str):
    '''
    逐行比较，按Differ 标记（+ - ？标记）
    :param a_lines:
    :param b_lines:
    :param name_a:
    :param name_b:
    :return:
    '''
    differ = difflib.Differ()
    result = list(differ.compare(a_lines, b_lines))

    print("\n"+"=" * 60)
    print("Differ")
    print("=" * 60)
    print(f" signal: - {name_a}")
    print(f"         + {name_b}")
    print(f"         f  差异位置 ")
    print("-"*60)

    for line in result:
        print(line,end="")

def main():
    a = read_lines(FILE_A)
    b = read_lines(FILE_B)

    show_side_by_side(a, b ,FILE_A.name,FILE_B.name)


if __name__ == "__main__":
    main()

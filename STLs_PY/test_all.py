#!/usr/bin/env python3
"""
测试所有STLs_PY示例文件
"""

import subprocess
import sys
import os


def run_python_file(filename):
    """运行Python文件并返回是否成功"""
    print(f"\n{'='*60}")
    print(f"测试: {filename}")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, filename], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            print(f"✓ {filename} 执行成功")
            # 只打印前几行输出，避免太多输出
            lines = result.stdout.strip().split("\n")
            if len(lines) > 5:
                print("输出预览:")
                for line in lines[:5]:
                    print(f"  {line}")
                print("  ...")
            else:
                print("输出:")
                for line in lines:
                    print(f"  {line}")
            return True
        else:
            print(f"✗ {filename} 执行失败")
            print(f"错误输出:\n{result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ {filename} 执行超时")
        return False
    except Exception as e:
        print(f"✗ {filename} 执行异常: {e}")
        return False


def main():
    print("开始测试所有STLs_PY示例文件")
    print(f"Python版本: {sys.version}")

    # 获取当前目录下所有.py文件（除了test_all.py本身）
    files = [
        f
        for f in os.listdir(".")
        if f.endswith(".py") and f != "test_all.py" and f != "__init__.py"
    ]

    files.sort()  # 按字母顺序排序

    success_count = 0
    total_count = len(files)

    for filename in files:
        if run_python_file(filename):
            success_count += 1

    print(f"\n{'='*60}")
    print("测试结果汇总")
    print("=" * 60)
    print(f"总文件数: {total_count}")
    print(f"成功: {success_count}")
    print(f"失败: {total_count - success_count}")

    if success_count == total_count:
        print("✓ 所有文件测试通过!")
        return 0
    else:
        print("✗ 部分文件测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

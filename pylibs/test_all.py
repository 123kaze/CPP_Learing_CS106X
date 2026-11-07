"""验证各标准库示例的算法结果、边界条件和独立运行入口。"""

import subprocess
import sys
import unittest
from datetime import date, timedelta
from math import inf
from pathlib import Path

from bisect_example import count_in_range, lis_length
from collections_example import bfs_distances, sliding_window_max
from datetime_example import (
    add_days,
    count_weekday,
    date_from_day_of_year,
    day_of_year,
    days_between,
)
from functools_example import count_grid_paths, fibonacci, largest_number
from heapq_example import dijkstra, minimum_merge_cost
from math_example import is_prime, lcm


class DatetimeTests(unittest.TestCase):
    def test_leap_day_and_signed_difference(self):
        start, end = date(2024, 2, 28), date(2024, 3, 1)
        self.assertEqual(days_between(start, end), 2)
        self.assertEqual(days_between(end, start), -2)
        self.assertEqual(days_between(start, start), 0)

    def test_date_offset(self):
        self.assertEqual(add_days(date(2024, 2, 28), 2), date(2024, 3, 1))
        self.assertEqual(add_days(date(2025, 1, 1), -1), date(2024, 12, 31))

    def test_day_of_year_and_inverse(self):
        for year in (1, 1900, 2000, 2024, 2025, 9999):
            for month, day in ((1, 1), (3, 1), (12, 31)):
                original = date(year, month, day)
                with self.subTest(original=original):
                    self.assertEqual(date_from_day_of_year(year, day_of_year(original)), original)
        self.assertEqual(day_of_year(date(2024, 2, 29)), 60)

    def test_invalid_day_number(self):
        for year, number in ((2024, 0), (2024, 367), (2025, 366), (0, 1)):
            with self.subTest(year=year, number=number):
                with self.assertRaises(ValueError):
                    date_from_day_of_year(year, number)

    def test_weekday_count_matches_enumeration(self):
        for start in (date(2024, 1, 1), date(2024, 2, 29), date(2024, 12, 31)):
            for length in range(1, 30):
                end = start + timedelta(days=length - 1)
                for weekday in range(7):
                    expected = sum((start + timedelta(days=i)).weekday() == weekday for i in range(length))
                    self.assertEqual(count_weekday(start, end, weekday), expected)

    def test_weekday_range_boundaries(self):
        self.assertEqual(count_weekday(date.max, date.max, date.max.weekday()), 1)
        self.assertEqual(count_weekday(date(2024, 1, 2), date(2024, 1, 1), 0), 0)
        with self.assertRaises(ValueError):
            count_weekday(date.min, date.max, 7)

    def test_datetime_traps(self):
        delta = timedelta(days=2, seconds=3)
        self.assertEqual(delta.seconds, 3)
        self.assertEqual(delta.total_seconds(), 172803)
        self.assertEqual(timedelta(seconds=-1).total_seconds(), -1)
        with self.assertRaises(ValueError):
            date(1900, 2, 29)
        self.assertEqual(date(2000, 2, 29).day, 29)


class AlgorithmTests(unittest.TestCase):
    def test_bfs_cycles_and_unreachable(self):
        self.assertEqual(bfs_distances([[1, 2], [0, 3], [0, 3], [1, 2], []], 0), [0, 1, 1, 2, -1])
        self.assertEqual(bfs_distances([[]], 0), [0])

    def test_sliding_window(self):
        self.assertEqual(sliding_window_max([1, 3, -1, -3, 5, 3, 6, 7], 3), [3, 3, 5, 5, 6, 7])
        self.assertEqual(sliding_window_max([2, 2, 2], 2), [2, 2])
        self.assertEqual(sliding_window_max([-2, -1], 1), [-2, -1])
        self.assertEqual(sliding_window_max([1, 2], 3), [])
        self.assertEqual(sliding_window_max([], 1), [])
        with self.assertRaises(ValueError):
            sliding_window_max([1], 0)

    def test_merge_cost(self):
        weights = [1, 2, 3, 4]
        self.assertEqual(minimum_merge_cost(weights), 19)
        self.assertEqual(weights, [1, 2, 3, 4])
        self.assertEqual(minimum_merge_cost(iter(weights)), 19)
        self.assertEqual(minimum_merge_cost([]), 0)
        self.assertEqual(minimum_merge_cost([7]), 0)
        with self.assertRaises(ValueError):
            minimum_merge_cost([-1, 2])

    def test_dijkstra_stale_states(self):
        graph = [[(1, 4), (2, 1)], [(3, 1)], [(1, 2), (3, 5)], [], []]
        self.assertEqual(dijkstra(graph, 0), [0, 3, 1, 4, inf])
        self.assertEqual(dijkstra([[(1, 0)], [(0, 0)]], 0), [0, 0])

    def test_range_count(self):
        nums = [1, 2, 2, 2, 4, 7]
        self.assertEqual(count_in_range(nums, 2, 4), 4)
        self.assertEqual(count_in_range(nums, 3, 3), 0)
        self.assertEqual(count_in_range(nums, 4, 2), 0)
        self.assertEqual(count_in_range([], 1, 2), 0)

    def test_lis(self):
        self.assertEqual(lis_length([10, 9, 2, 5, 3, 7, 101, 18]), 4)
        self.assertEqual(lis_length([2, 2, 2]), 1)
        self.assertEqual(lis_length([3, 2, 1]), 1)
        self.assertEqual(lis_length([]), 0)

    def test_integer_math(self):
        self.assertEqual(lcm(18, 24), 72)
        self.assertEqual(lcm(-3, 4), 12)
        self.assertEqual(lcm(0, 0), 0)
        self.assertEqual([n for n in range(-2, 21) if is_prime(n)], [2, 3, 5, 7, 11, 13, 17, 19])
        self.assertFalse(is_prime(49))

    def test_fibonacci_cache(self):
        fibonacci.cache_clear()
        self.assertEqual(fibonacci(0), 0)
        self.assertEqual(fibonacci(1), 1)
        self.assertEqual(fibonacci(10), 55)
        hits = fibonacci.cache_info().hits
        self.assertEqual(fibonacci(10), 55)
        self.assertEqual(fibonacci.cache_info().hits, hits + 1)
        with self.assertRaises(ValueError):
            fibonacci(-1)

    def test_grid_paths_and_separate_caches(self):
        self.assertEqual(count_grid_paths(3, 3), 6)
        self.assertEqual(count_grid_paths(3, 3, [(1, 1)]), 2)
        self.assertEqual(count_grid_paths(3, 3), 6)
        self.assertEqual(count_grid_paths(1, 1), 1)
        self.assertEqual(count_grid_paths(1, 1, [(0, 0)]), 0)
        self.assertEqual(count_grid_paths(0, 3), 0)

    def test_largest_number(self):
        self.assertEqual(largest_number([3, 30, 34, 5, 9]), "9534330")
        self.assertEqual(largest_number([12, 121]), "12121")
        self.assertEqual(largest_number([0, 0]), "0")
        self.assertEqual(largest_number([]), "")


class EntryPointTests(unittest.TestCase):
    def test_each_example_runs_independently(self):
        directory = Path(__file__).resolve().parent
        expected_outputs = {
            "datetime_example.py": "2024-02-28 的 2 天后: 2024-03-01",
            "collections_example.py": "滑动窗口最大值: [3, 3, 5, 5, 6, 7]",
            "heapq_example.py": "合并 [1, 2, 3, 4] 的最小代价: 19",
            "bisect_example.py": "最长严格递增子序列长度: 4",
            "math_example.py": "不考虑障碍的 3x4 网格路径数: 10",
            "itertools_example.py": "游程编码 aaabbcaa: [('a', 3), ('b', 2), ('c', 1), ('a', 2)]",
            "functools_example.py": "拼接最大数 [3, 30, 34, 5, 9]: 9534330",
        }
        paths = sorted(directory.glob("*_example.py"))
        self.assertEqual({path.name for path in paths}, set(expected_outputs))
        for path in paths:
            with self.subTest(module=path.name):
                result = subprocess.run(
                    [sys.executable, "-B", str(path)],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("用法示例", result.stdout)
                self.assertIn("示例结束", result.stdout)
                self.assertIn(expected_outputs[path.name], result.stdout)

    def test_imports_do_not_print(self):
        directory = Path(__file__).resolve().parent
        modules = sorted(path.stem for path in directory.glob("*_example.py"))
        result = subprocess.run(
            [sys.executable, "-B", "-c", "import " + ", ".join(modules)],
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)

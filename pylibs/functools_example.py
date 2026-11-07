"""
@file functools_example.py
@brief Python functools 用法示例：记忆化搜索和自定义排序

特点与复杂度：
1. lru_cache(maxsize=None) 缓存所有状态，适合动态规划和记忆化搜索。
2. 缓存参数必须可哈希，list / dict 不能直接作为缓存键。
3. 记忆化 Fibonacci 有 O(n) 个状态，仍有 O(n) 递归深度。
4. 网格路径搜索至多 O(rows*cols) 个状态，递归深度 O(rows+cols)。
5. cmp_to_key 把比较函数转换为排序键；能用普通 key 时优先用普通 key。
以上 DP 复杂度按单次整数加法 O(1) 计，大整数需要额外位运算成本。
"""

from functools import cmp_to_key, lru_cache, reduce


@lru_cache(maxsize=None)
def fibonacci(n):
    """记忆化 Fibonacci，F(0)=0，F(1)=1；只适合递归深度较小的输入。"""
    if n < 0:
        raise ValueError("n 必须非负")
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def count_grid_paths(rows, cols, blocked=()):
    """从 (0,0) 到右下角，只能向右 / 下走；障碍坐标从 0 开始。"""
    if rows < 0 or cols < 0:
        raise ValueError("网格大小必须非负")
    obstacles = frozenset(blocked)

    # 每次调用创建自己的缓存，避免不同网格之间复用旧结果。
    @lru_cache(maxsize=None)
    def search(row, col):
        if row >= rows or col >= cols or (row, col) in obstacles:
            return 0
        if row == rows - 1 and col == cols - 1:
            return 1
        return search(row + 1, col) + search(row, col + 1)

    return search(0, 0)


def largest_number(nums):
    """将非负整数拼接成最大的十进制数字字符串，空输入返回空字符串。"""
    if not nums:
        return ""

    def compare(a, b):
        ab, ba = a + b, b + a
        return (ab < ba) - (ab > ba)

    parts = sorted(map(str, nums), key=cmp_to_key(compare))
    return "".join(parts).lstrip("0") or "0"


def main():
    print("========== Python functools 用法示例 ==========")

    # 1. 记忆化递归
    print("\n1. lru_cache 记忆化搜索:")
    fibonacci.cache_clear()
    print(f"F(10): {fibonacci(10)}")
    print(f"缓存统计: {fibonacci.cache_info()}")
    print(f"再次求 F(10): {fibonacci(10)}")
    print(f"再次调用后的缓存统计: {fibonacci.cache_info()}")

    # 2. 带障碍网格路径数
    print("\n2. 网格路径计数:")
    print(f"3x3 无障碍网格: {count_grid_paths(3, 3)}")
    print(f"3x3 网格，中心 (1,1) 有障碍: {count_grid_paths(3, 3, [(1, 1)])}")

    # 3. 自定义比较规则
    print("\n3. cmp_to_key 自定义排序:")
    nums = [3, 30, 34, 5, 9]
    print(f"拼接最大数 {nums}: {largest_number(nums)}")
    print(f"全零输入 [0, 0]: {largest_number([0, 0])}")
    print("比较规则: 若 a+b > b+a，则 a 应排在 b 前面")

    # 4. 累积归约
    print("\n4. reduce 累积归约:")
    print(f"带初值 1 的连乘: {reduce(lambda a, b: a * b, [2, 3, 4], 1)}")
    print("求和、连乘优先使用 sum / math.prod，通常更清楚")

    # 5. 性能和易错点
    print("\n5. 性能和易错点:")
    print("1. 默认 lru_cache 只保留 128 个状态；DP 通常显式设 maxsize=None")
    print("2. 缓存不消除递归深度限制，规模大时改写成迭代 DP")
    print("3. 可变参数应转换为 tuple 等可哈希类型，注意缓存所依赖的外部状态")
    print("4. 多组测试数据可能需要 cache_clear()，或像网格示例一样创建局部缓存")
    print("5. 比较函数返回负数 / 0 / 正数，不是 True / False")
    print("\n========== functools 示例结束 ==========")


if __name__ == "__main__":
    main()

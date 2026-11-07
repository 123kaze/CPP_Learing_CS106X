"""
@file itertools_example.py
@brief Python itertools 用法示例：枚举、前缀和和分组

特点与复杂度：
1. 返回迭代器，按需生成结果，不必一次存入列表。
2. 全排列有 n! 个，每个元组长度 n，完整枚举 O(n! * n)。
3. k 元组合有 C(n,k) 个，完整枚举 O(C(n,k) * k)。
4. m 个长度为 n 的集合做笛卡尔积有 n**m 个结果。
5. accumulate 处理 n 个元素需要 O(n) 次加法。
"""

from itertools import (
    accumulate,
    chain,
    combinations,
    combinations_with_replacement,
    groupby,
    permutations,
    product,
)


def main():
    print("========== Python itertools 用法示例 ==========")

    # 1. 排列：顺序不同就是不同结果
    print("\n1. permutations 排列:")
    print(f"[1, 2, 3] 的长度 2 排列: {list(permutations([1, 2, 3], 2))}")
    print(f"重复值仍按位置枚举: {list(permutations([1, 1, 2], 2))}")

    # 2. 组合：忽略顺序
    print("\n2. combinations 组合:")
    print(f"从 [1, 2, 3] 选 2 个: {list(combinations([1, 2, 3], 2))}")
    print(f"允许重复选择: {list(combinations_with_replacement([1, 2, 3], 2))}")

    # 3. 笛卡尔积：每一位独立选择
    print("\n3. product 笛卡尔积:")
    print(f"两个集合组合: {list(product([1, 2], ['A', 'B']))}")
    print(f"长度 3 的二进制状态: {list(product([0, 1], repeat=3))}")

    # 4. 前缀和与扁平化
    print("\n4. accumulate 和 chain:")
    nums = [2, 1, 3, 4]
    prefix = list(accumulate(nums, initial=0))
    left, right = 1, 3
    print(f"数组: {nums}, 带前导 0 的前缀和: {prefix}")
    print(f"下标区间 [{left}, {right}) 的和: {prefix[right] - prefix[left]}")
    print(f"链式展开: {list(chain.from_iterable([[1, 2], [], [3, 4]]))}")

    # 5. 连续分组
    print("\n5. groupby 连续分组:")
    runs = [(key, len(list(group))) for key, group in groupby("aaabbcaa")]
    print(f"游程编码 aaabbcaa: {runs}")
    words = ["ant", "cat", "bear", "dog", "ox"]
    groups = [(length, list(group)) for length, group in groupby(sorted(words, key=len), key=len)]
    print(f"先按长度排序再分组: {groups}")

    # 6. 算法应用与性能提示
    print("\n6. 算法题应用和性能提示:")
    nums = [1, 2, 3, 4]
    pairs = [pair for pair in combinations(nums, 2) if sum(pair) == 5]
    print(f"枚举和为 5 的二元组合: {pairs}")
    print("1. permutations 和 combinations 根据元素位置枚举，不自动去重")
    print("2. groupby 只合并连续相同的键，且分组迭代器应立即消费")
    print("3. 迭代器使用一次后会耗尽；上述 list(...) 仅用于小规模演示")
    print("4. 惰性生成不降低枚举数量，大规模排列组合会超时")
    print("\n========== itertools 示例结束 ==========")


if __name__ == "__main__":
    main()

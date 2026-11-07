"""
@file bisect_example.py
@brief Python bisect 用法示例：二分边界、区间计数和 LIS

特点与复杂度：
1. bisect_left 是第一个 >= x 的位置，类似 C++ lower_bound。
2. bisect_right 是第一个 > x 的位置，类似 C++ upper_bound。
3. 两种二分查找为 O(log n)，前提是序列已经有序。
4. insort 在列表中插入为 O(n)，查找位置快不代表插入快。
5. 本示例求最长严格递增子序列长度为 O(n log n)，空间 O(n)。
"""

from bisect import bisect_left, bisect_right, insort_left


def count_in_range(sorted_nums, low, high):
    """统计升序数组中位于闭区间 [low, high] 的元素数，包括重复值。"""
    if low > high:
        return 0
    return bisect_right(sorted_nums, high) - bisect_left(sorted_nums, low)


def lis_length(nums):
    """最长严格递增子序列长度，重复值不增加长度。"""
    tails = []
    for value in nums:
        position = bisect_left(tails, value)
        # tails[i] 是长度 i+1 的递增子序列能取得的最小末尾值。
        if position == len(tails):
            tails.append(value)
        else:
            tails[position] = value
    return len(tails)


def main():
    print("========== Python bisect 用法示例 ==========")

    # 1. 左边界和右边界
    print("\n1. 二分边界:")
    nums = [1, 2, 2, 2, 4, 7]
    left, right = bisect_left(nums, 2), bisect_right(nums, 2)
    print(f"有序数组: {nums}")
    print(f"2 的左边界: {left}, 右边界: {right}, 出现次数: {right - left}")
    print(f"不存在的 3 的插入位置: {bisect_left(nums, 3)}")
    print(f"比所有元素大的 9 的插入位置: {bisect_left(nums, 9)}")

    # 2. 判断存在性和限定查找范围
    print("\n2. 判断存在性和限定范围:")
    target = 3
    index = bisect_left(nums, target)
    exists = index < len(nums) and nums[index] == target
    print(f"3 是否存在: {exists}")
    print(f"只在下标 [2, 5) 内找 2 的左边界: {bisect_left(nums, 2, 2, 5)}")

    # 3. 维护有序列表
    print("\n3. 有序插入:")
    insort_left(nums, 3)
    print(f"插入 3 后: {nums}")

    # 4. 算法应用
    print("\n4. 算法题应用:")
    print(f"闭区间 [2, 4] 内元素数: {count_in_range(nums, 2, 4)}")
    values = [10, 9, 2, 5, 3, 7, 101, 18]
    print(f"数组: {values}, 最长严格递增子序列长度: {lis_length(values)}")
    print(f"[2, 2, 2] 的严格递增长度: {lis_length([2, 2, 2])}")

    # 5. 易错点
    print("\n5. 易错点:")
    print("1. 二分返回插入位置，不保证该位置存在目标值，也可能等于 len(nums)")
    print("2. low / high 参数是下标范围，右端不包含；值域区间需用两次二分")
    print("3. LIS 若要求非递减序列，把 bisect_left 换成 bisect_right")
    print("4. tails 用于求长度，不保证本身是原数组中的一条子序列")
    print("\n========== bisect 示例结束 ==========")


if __name__ == "__main__":
    main()

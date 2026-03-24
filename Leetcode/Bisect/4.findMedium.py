from typing import List

class Solution:
    def findMedianSortedArrays(self, nums1: List[int], nums2: List[int]) -> float:
        # 确保 nums1 是较短的数组
        if len(nums1) > len(nums2):
            return self.findMedianSortedArrays(nums2, nums1)

        n = len(nums1)  # 较短数组长度
        m = len(nums2)  # 较长数组长度
        total_left = (n + m + 1) // 2  # 左边部分元素个数

        left, right = 0, n

        while left <= right:  # 改为 <=
            i = (left + right) // 2  # nums1 的分割点
            j = total_left - i       # nums2 的分割点

            # 边界处理 - 注意区分 n 和 m
            left1 = nums1[i - 1] if i > 0 else float('-inf')
            right1 = nums1[i] if i < n else float('inf')  # 用 n，不是 m
            left2 = nums2[j - 1] if j > 0 else float('-inf')
            right2 = nums2[j] if j < m else float('inf')  # 用 m，不是 n

            if left1 <= right2 and left2 <= right1:
                # 找到正确分割
                if (n + m) % 2 == 0:
                    return (max(left1, left2) + min(right1, right2)) / 2
                else:
                    return max(left1, left2)
            elif left1 > right2:
                # i 太大，需要减小 i
                right = i - 1
            else:
                # left2 > right1，i 太小，需要增大 i
                left = i + 1
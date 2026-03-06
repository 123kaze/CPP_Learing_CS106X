from typing import List


class Solution:
    def productExceptSelf(self, nums: List[int]) -> List[int]:
        if not nums:
            return []
        res = []
        n = len(nums)
        left = [1 for _ in range(n)]
        right = [1] * n

        for i in range(1, n):
            left[i] = left[i - 1] * nums[i - 1]
        print(left)
        for i in range(n - 2, -1, -1):
            right[i] = right[i + 1] * nums[i + 1]
        print(right)
        res = [right[j] * left[j] for j in range(n)]
        return res


s = Solution()
print(s.productExceptSelf([1, 2, 3, 4]))

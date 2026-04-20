from functools import cache
from typing import List
class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        n = len(nums)
        @cache
        def dfs(i):
            '''
            :param i: 当前坐标为i
            :return: 当前角标为结尾能够达到的连续子数组的和
            dfs(i) = max(dfs(i-1) + nums[i], nums[i])
            '''
            if i == 0:
                return nums[i]
            return max(dfs(i-1),0)+nums[i]
        return dfs(n-1)

class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        f = [0] * len(nums)
        f[0] = nums[0]
        for i in range(1, len(nums)):
            f[i] = max(f[i - 1], 0) + nums[i]
        return max(f)

# 作者：灵茶山艾府
# 链接：https://leetcode.cn/problems/maximum-subarray/
# 来源：力扣（LeetCode）
# 著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。




from typing import List
class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        current = maxs = nums[0]
        for num in nums[1:]:
            current = max(current + num, num)
            maxs = max(maxs, current)

        return maxs

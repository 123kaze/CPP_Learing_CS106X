from typing import List

class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        n = len(nums)
        i = j = s = 0
        res = nums[0]
        for k in range(n):
            s+=nums[k]
            res = max(s,res)
            if s<0:
                s = 0


        return res

s = Solution()
print(s.maxSubArray([-1,0,-2]))
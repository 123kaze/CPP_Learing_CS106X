from typing import List

class Solution:
    def canJump(self, nums: List[int]) -> bool:
        n = len(nums)-1
        maxLength = 0
        for i,v in enumerate(nums):
            if i <= maxLength:
                maxLength = max(maxLength,nums[i]+i)
            else:
                continue
            if maxLength >= n:
                return True
        return False
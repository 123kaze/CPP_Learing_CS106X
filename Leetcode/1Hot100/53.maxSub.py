from typing import List

class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        n = len(nums)
        prefix = [0 for _ in range(n)]
        '''
        cur,if cur + now <0,jump and break
        '''
        max1 = -99999
        j = 0
        cur = 0
        for i,v in enumerate(nums):
            cur = cur+v
            max1 = max(max1,cur)
            if cur<=0:
                cur = 0
                continue

        return max1


from typing import List

class Solution:
    def jump(self, nums: List[int]) -> int:
        res = 0
        n = len(nums)
        maxp,end,step = 0,0,0
        for i in range(n-1):
            if maxp >=i:
                maxp = max(maxp,i+nums[i])

                if i == end:
                    end = maxp
                    step+=1

        return step
    
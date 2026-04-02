from typing import List
class Solution:
    def rob(self, nums: List[int]) -> int:
        f0 = f1 = 0
        for i,x in enumerate(nums):
            newf = max(f1,f0+x)
            f0 = f1
            f1 = newf
        return f1
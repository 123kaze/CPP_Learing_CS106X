from typing import List
from collections import defaultdict
class Solution:
    def maxSum(self, nums: List[int], m: int, k: int) -> int:
        res = 0
        cur = 0
        n = len(nums)
        d = defaultdict()

        for i in range(k):
            num = nums[i]
            d[num] = d.get(num,0)+1
            cur+=num
        
        if len(d)>=m:
            res = cur

        for i in range(k,n):
            l = nums[i-k]
            d[l] -=1
            if d[l] == 0:
                del d[l]
            cur -= l
            cur += nums[i]
            r = nums[i]
            d[r] = d.get(r,0)+1
            
            if len(d) >= m:
                res = max(cur,res)

        return res
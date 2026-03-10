from typing import List
from collections import defaultdict
class Solution:
    def maxSubarrayLength(self, nums: List[int], k: int) -> int:
        if not nums:
            return 0
        if k==0:
            return 0
        
        res = 1
        n = len(nums)
        d = defaultdict()
        l =r =  0

        for r in range(n):
            d[nums[r]] = d.get(nums[r],0)+1
            if d[nums[r]] >k:
                le = r-l
                res = max(res,le)
                while(l<r and d[nums[r]]>k):
                    d[nums[l]] -=1
                    l+=1
            if r == n-1:
                le = r-l+1
                res = max(res,le)


        return res
    

s = Solution()
s.maxSubarrayLength([1,1000000000],2)
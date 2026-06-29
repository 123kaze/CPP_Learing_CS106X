from typing import List
from functools import cache
class Solution:
    def tallestBillboard(self, nums: List[int]) -> int:
        n = len(nums)
        s = sum(nums)
        s1 = s//2
        @cache
        def dfs(i,c):
            '''
            i 当前i号
            c 当前空余
            dfs(i,c) = dfs(i-1,c)+dfs(i-1,c-v)
            '''
            if i<0 :
                return 1 if c==0 else 0
            if c < nums[i]:
                return dfs(i-1,c)
            
            return dfs(i-1,c)+dfs(i-1,c-nums[i])

        for i in range(s1,-1,-1):
            if dfs(n-1,i)>1:
                return i
        return 0

s = Solution()
print(s.tallestBillboard([1,2]))
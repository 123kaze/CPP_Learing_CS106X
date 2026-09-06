from functools import lru_cache

class Solution:
    def climbStairs(self, n: int) -> int:
        @lru_cache(None)
        def dfs(n):
            '''
            dfs(n) = dfs(n-1)+dfs(n-2)
            2 = 2
            1 = 1
            3 = 3
            '''
            if n<0:
                return None
            if n==1:
                return 1
            if n ==0:
                return 1
            return dfs(n-1)+dfs(n-2)

        return dfs(n)
                

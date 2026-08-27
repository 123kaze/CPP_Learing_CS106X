from typing import List
from functools import lru_cache
class Solution:
    def combinationSum2(self, candidates: List[int], target: int) -> List[List[int]]:
        n = len(candidates)
        res = []
        candidates.sort()
        path = []
        def dfs(i,need):
            '''
            dfs(i,need) = dfs(i-1,need)
            '''
            if need == 0:
                res.append(path[:])
                return
            if i<0:
                return 
            x = candidates[i]
            if need >= x:
                 
                path.append(x)
                dfs(i-1,need-x)
                path.pop()
            while i>-1 and candidates[i] ==x:
                i-=1
            dfs(i,need)
        dfs(n-1,target)
        return res


from typing import List
from functools import lru_cache

class Solution:
    def permute(self, nums: List[int]) -> List[List[int]]:
        n = len(nums)    
        res = []   
        visited = [False for _ in range(n)]

        def backtrack(nums,cur):
            if len(cur) == n:
                res.append(cur[:])
                return
            for i in range(n):
                if not visited[i] :
                    cur.append(nums[i])
                    visited[i] = True
                    backtrack(nums,cur)
                    visited[i] = False
                    cur.pop()

        backtrack(nums,[])
        return res
            
            
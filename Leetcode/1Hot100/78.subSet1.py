from typing import List

class Solution:
    def subsets(self, nums: List[int]) -> List[List[int]]:
        res = []
        n = len(nums)

        if not nums:
            return []
        visited = [0 for _ in range(n)]
        def backtrack(i,path):
            '''
            
            '''
            if i>=n:
                return 

            for j in range(i,n):
                if not visited[j]:
                    path.append(nums[j])
                    visited[j] = 1
                    res.append(path[:])
                    backtrack(j+1,path)
                    path.pop(nums[j])
                    visited[j] = 0
        backtrack(0,[])
        return res

                
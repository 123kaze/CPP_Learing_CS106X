from typing import List
class Solution:
    def permute(self, nums: List[int]) -> List[List[int]]:
        n = len(nums)
        visited = [ 0 for _ in range(n)]
        res = []
        def backtrack(num,visited,i):
            if i == n:
                res.append(num[:])
                return
            for j in range(n):
                if not visited[j]:
                    num.append(nums[j])
                    visited[j]=1
                    backtrack(num,visited,i+1)
                    num.pop()
                    visited[j]=0

        backtrack([],visited,0)
        return res 
s = Solution()
print(s.permute([1,2,3]))
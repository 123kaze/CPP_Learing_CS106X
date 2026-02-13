from typing import List
class Solution:
    def subsets(self, nums: List[int]) -> List[List[int]]:
        n = len(nums)
        visited = [0]*n
        res = [[]]
        def backtack(cur,visited,i):
            if i == n:
                res.append(cur[:])
                return
            if not visited[j]:
                cur.append(nums[i])
                visited[i]=1
                backtack(cur,visited,i+1)
                cur.pop()
                backtack(cur,visited,i+1)
        
        backtack(0,visited,0)
        return res


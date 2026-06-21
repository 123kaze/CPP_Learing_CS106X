from typing import List


class Solution:
    def permute(self, nums: List[int]) -> List[List[int]]:
        res = []
        n = len(nums)
        visited = [False]*(n+1)
        def dfs(i,path):
            nonlocal visited
            if len(path) == n:
                res.append(path[:])
                return
            for j in range(n):
                if visited[j]:
                    continue
                path.append(nums[j])
                visited[j] = True
                dfs(j+1,path)
                path.pop()
                visited[j]=False
        return res


s = Solution()
print(s.permute([1]))


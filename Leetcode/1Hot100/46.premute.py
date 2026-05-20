from typing import List


class Solution:
    def permute(self, nums: List[int]) -> List[List[int]]:
        res = []
        n = len(nums)
        visited = [0] * n

        def dfs(i, path):
            if len(path) == n:
                res.append(path[:])
                return
            for j in range(n):
                if visited[j] == 0:
                    visited[j] = 1
                    path.append(nums[j])
                    dfs(j, path)
                    path.pop()
                    visited[j] = 0

        dfs(0, [])
        return res


s = Solution()
print(s.permute([1, 2, 3]))

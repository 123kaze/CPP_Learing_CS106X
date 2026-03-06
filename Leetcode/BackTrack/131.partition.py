from typing import List


class Solution:
    def partition(self, s: str) -> List[List[str]]:
        n = len(s)
        res = []
        path = []

        def dfs(idx):
            if idx == n:
                res.append(path[:])
                return

            for i in range(idx, n):
                t = s[idx : i + 1]
                if t == t[::-1]:
                    path.append(t[:])
                    dfs(i + 1)
                    path.pop()

        dfs(0)
        return res

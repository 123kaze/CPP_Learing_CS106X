from typing import List
from functools import lru_cache

class Solution:
    def maximalSquare(self, matrix: List[List[str]]) -> int:
        m = len(matrix)

        n = len(matrix[0])

        @lru_cache(maxsize=None)
        def dfs(i,j):
            '''
            :param i:
            :param j:
            :return: 以ij为右下角的时候，最大的边长是
            dfs(i,j) = min(dfs(i-1,j-1),dfs(i-1,j),dfs(i,j-1))+1
            '''
            if i<0 or j<0 or i>=m or j>=n: return 0

            return min(dfs(i-1,j-1),dfs(i-1,j),dfs(i,j-1))+1 if matrix[i][j] == '1' else 0
        res = 0
        for i in range(m):
            for j in range(n):
                if matrix[i][j] == '1':
                    res = max(dfs(i,j),res)

        return res**2

s = Solution()
print(s.maximalSquare([["1","0","1","1","0","1"],["1","1","1","1","1","1"],["0","1","1","0","1","1"],["1","1","1","0","1","0"],["0","1","1","1","1","1"],["1","1","0","1","1","1"]]))
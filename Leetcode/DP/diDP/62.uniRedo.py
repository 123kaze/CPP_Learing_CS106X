from functools import cache
class Solution:
    def uniquePaths(self, m: int, n: int) -> int:
        @cache
        def dfs(i, j):
            '''
            dfs(i, j) = dfs(i-1,j) + dfs(i,j-1)
            :param i:
            :param j:
            :return: amount of Paths to (i,j)
            '''
            if i == 0 and j == 0:
                return 1
            if i < 0 or j < 0 or i >= m or j >= n:
                return 0
            return dfs(i, j-1) + dfs(i-1, j)
        


        return dfs(m-1, n-1)


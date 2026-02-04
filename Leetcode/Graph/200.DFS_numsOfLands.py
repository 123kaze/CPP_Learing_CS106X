import queue
from collections import deque
class Solution:
    def numIslands(self, grid: List[List[str]]) -> int:
        m = len(grid)
        n = len(grid[0])
        maxl = 0
        def dfs(grid,i,j):
            if i>=m or i<0 or j>=n or j<0 or grid[i][j] == '0':
                return
            elif 0<=i<m and 0<=j<n:
                grid[i][j] = '0'
                dfs(grid,i+1,j)
                dfs(grid,i,j+1)
                dfs(grid,i-1,j)
                dfs(grid,i,j-1)
        
    
        for i in range(m):
            for j in range(n):
                if grid[i][j] == '1':
                    maxl+=1
                    dfs(grid,i,j)

        return maxl
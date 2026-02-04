import queue
from collections import deque
class Solution:
    def numIslands(self, grid: List[List[str]]) -> int:
        
        
        m = len(grid)
        maxl=0
        n = len(grid[0])
        
        
        def BFS(grid,i,j):
            q = deque()
            q.append((i,j))
        
            while(q):
                i,j = q.popleft()
                if i>=m or i<0 or j>=n or j<0 or grid[i][j] == '0':
                    continue
                else:
                    grid [i][j] = '0'
                    dire = [(1,0),(-1,0),(0,1),(0,-1)]
                    for di,dj in dire:
                        newi = i+di
                        newj = j+dj
                        q.append((newi,newj))

        for i in range(m):
            for j in range(n):
                if grid[i][j] == '1':
                    maxl+=1
                    BFS(grid,i,j)
        
        return maxl
    

# another
"""class Solution:
    def numIslands(self, grid: List[List[str]]) -> int:
        nr = len(grid)
        if nr == 0:
            return 0
        nc = len(grid[0])

        num_islands = 0
        for r in range(nr):
            for c in range(nc):
                if grid[r][c] == "1":
                    num_islands += 1
                    grid[r][c] = "0"
                    neighbors = collections.deque([(r, c)])
                    while neighbors:
                        row, col = neighbors.popleft()
                        for x, y in [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]:
                            if 0 <= x < nr and 0 <= y < nc and grid[x][y] == "1":
                                neighbors.append((x, y))
                                grid[x][y] = "0"
        
        return num_island
"""
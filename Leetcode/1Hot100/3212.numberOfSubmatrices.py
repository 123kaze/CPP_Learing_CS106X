from typing import List
from collections import deque

class Solution:
    def numberOfSubmatrices(self, grid: List[List[str]]) -> int:
        '''
        0,0
        'X' 和 'Y' 的频数相等
        至少包含一个 'X'
        '''
        q = deque()
        m = len(grid)
        n = len(grid[0])
        node = (0,0)
        visited = [[False] * n for _ in range(m)]
        xi = 1 if grid[0][0] == 'X' else 0
        yi = 1 if grid[0][0] == 'Y' else 0
        q.append((0, 0, xi, yi))
        dire = [(0,1),(1,0)]
        res = 0
        if xi >0 and xi == yi:
            res+=1
        while q:
            x,y,curx,cury = q.popleft()
            for dx,dy in dire:
                nx,ny = dx+x,dy+y
                if 0<=nx<m and 0<=ny<n and not visited[nx][ny]:
                    
                    visited[nx][ny] = True
                    totalX = 0
                    totalY = 0
                    for i in range(nx + 1):
                        for j in range(ny + 1):
                            if grid[i][j] == 'X':
                                totalX += 1
                            elif grid[i][j] == 'Y':
                                totalY += 1
                    if totalX > 0 and totalX == totalY:
                        res += 1
                    q.append((nx,ny,totalX,totalY))
                else:
                    continue

        return res


from typing import List

class Solution:
    def numberOfSubmatrices(self, grid: List[List[str]]) -> int:
        m = len(grid)
        n = len(grid[0])
        
        # dpX[i][j] 表示从 (0,0) 到 (i,j) 的矩形中 X 的数量
        # dpY[i][j] 表示从 (0,0) 到 (i,j) 的矩形中 Y 的数量
        dpX = [[0] * n for _ in range(m)]
        dpY = [[0] * n for _ in range(m)]
        
        res = 0
        
        for i in range(m):
            for j in range(n):
                # 计算当前格子是 X 还是 Y
                x = 1 if grid[i][j] == 'X' else 0
                y = 1 if grid[i][j] == 'Y' else 0
                
                # 二维前缀和
                if i == 0 and j == 0:
                    dpX[i][j] = x
                    dpY[i][j] = y
                elif i == 0:
                    dpX[i][j] = dpX[i][j-1] + x
                    dpY[i][j] = dpY[i][j-1] + y
                elif j == 0:
                    dpX[i][j] = dpX[i-1][j] + x
                    dpY[i][j] = dpY[i-1][j] + y
                else:
                    dpX[i][j] = dpX[i-1][j] + dpX[i][j-1] - dpX[i-1][j-1] + x
                    dpY[i][j] = dpY[i-1][j] + dpY[i][j-1] - dpY[i-1][j-1] + y
                
                # 检查是否满足条件
                if dpX[i][j] > 0 and dpX[i][j] == dpY[i][j]:
                    res += 1
        
        return res
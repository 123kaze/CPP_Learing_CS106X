from typing import List
from collections import deque
class Solution:
    def minimumEffortPath(self, heights: List[List[int]]) -> int:
        q = deque()
        res = 999999
        m = len(heights)
        n = len(heights[0])
        dire = [(1,0),(0,1),(-1,0),(0,-1)]
        


        def canReach(limit):
            start = (0,0)
            q.append(start)
            visited = [[False] * n for _ in range(m)]

            while q:
                x,y = q.popleft()
                if x == m-1 and y == n-1:
                    return True

                for dx,dy in dire:
                    nx,ny = dx+x,dy+y

                    if nx<0 or ny<0 or nx >= m or ny >= m:
                        continue
                    if visited[nx][ny]:
                        continue

                    diff = abs(heights[nx][ny] - heights[x][y])

                    if diff <= limit:
                        visited[nx][ny] = True
                        q.append((nx, ny))
            
            return False        

        left = 0
        right = 10**6
        while left <= right:
            mid = left+(right-left)//2
            if canReach(mid):
                right = mid-1
            else:
                left = mid+1

        return left
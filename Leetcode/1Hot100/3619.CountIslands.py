from typing import List
class Solution:
    def countIslands(self, grid: List[List[int]], k: int) -> int:
        m = len(grid)
        n = len(grid[0])
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        def dfs(x, y):
            '''
            dfs(x,y) = sum(dfs)
            :param x:
            :param y:
            :return: num
            '''
            if grid[x][y] == 0:
                return 0
            nums = grid[x][y]
            grid[x][y] = 0
            for dx, dy in directions:
                nx,ny = x + dx, y + dy
                if 0 <= nx < m and 0 <= ny < n and grid[nx][ny] != 0:
                    nums+=dfs(nx,ny)

            return nums

        res = []
        count = 0
        for i in range(m):
            for j in range(n):
                if grid[i][j] > 0:
                    res.append(dfs(i,j))
        for r in res:
            if r !=0 and r%k == 0:
                count += 1

        return count


s = Solution()
print(s.countIslands([[0,2,1,0,0],[0,5,0,0,5],[0,0,1,0,0],[0,1,4,7,0],[0,2,0,0,8]],5))


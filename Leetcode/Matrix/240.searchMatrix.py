from typing import List
class Solution:
    def searchMatrix(self, matrix: List[List[int]], target: int) -> bool:
        m = len(matrix)
        n = len(matrix[0])
        flag = False
        dire = [(1,0),(0,1)]
        def dfs(i, j):
            if i<0 or i>=m or j<0 or j>=n or matrix[i][j] > target:
                return
            if matrix[i][j] == target:
                return True
            flag = False
            if 0<=i<m and 0<=j<n and matrix[i][j] < target :
                for dx,dy in dire:
                    nx,ny = i+dx,j+dy
                    flag = dfs(nx,ny) if flag != True else True
            return flag
        flag = dfs(0,0)
        return flag == True


    from typing import List

class Solution:
    def searchMatrix(self, matrix: List[List[int]], target: int) -> bool:
        if not matrix or not matrix[0]:
            return False

        m, n = len(matrix), len(matrix[0])
        i, j = 0, n - 1  # 从右上角开始

        while i < m and j >= 0:
            if matrix[i][j] == target:
                return True
            elif matrix[i][j] > target:
                j -= 1  # 当前值太大，向左移动
            else:
                i += 1  # 当前值太小，向下移动

        return False

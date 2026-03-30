from typing import List
class Solution:
    def setZeroes(self, matrix: List[List[int]]) -> None:
        """
        Do not return anything, modify matrix in-place instead.
        """
        n = len(matrix)
        m = len(matrix[0])
        need = []
        for i in range(n):
            for j in range(m):
                if matrix[i][j] == 0:
                    need.append((i, j))

        while need:
            i, j = need.pop()
            for t in range(n):
                matrix[t][j] = 0
            for q in range(m):
                matrix[i][q] = 0




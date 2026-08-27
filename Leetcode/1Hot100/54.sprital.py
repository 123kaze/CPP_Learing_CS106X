from typing import List

class Solution:
    def spiralOrder(self, matrix: List[List[int]]) -> List[int]:
        m = len(matrix)
        n = len(matrix[0])

        res = []
        dires = [[0,1],[1,0],[0,-1],[-1,0]]
        i = j =0
        di = 0
        for _ in range(m*n):
            res.append(matrix[i][j])
            matrix[i][j] = None
            dx,dy = dires[di]
            nx ,ny = dx+i,dy+j
            if nx<0 or nx>=m or ny<0 or ny>=n or matrix[nx][ny] == None:
                di = (di+1)%4
            i,j = i+dires[di][0],j+dires[di][1]

        return res

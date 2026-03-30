DIRS = (0, 1), (1, 0), (0, -1), (-1, 0)
from typing import List
class Solution:
    def spiralOrder(self, matrix: List[List[int]]) -> List[int]:
        '''

        :param matrix:
        :return:
        '''
        if not matrix:
            return []
        n = len(matrix)
        m = len(matrix[0])
        res = []
        i=j=dir=0
        for _ in range(m*n):
            res.append(matrix[i][j])
            matrix[i][j]=None
            x,y = i+DIRS[dir][0],j+DIRS[dir][1]
            if x<0 or y<0 or x>=n or y>=m or matrix[x][y] is None:
                dir = (dir+1)%4
            i += DIRS[dir][0]
            j += DIRS[dir][1]
        return res

from typing import List
class Solution:
    def minCost(self, startPos: List[int], homePos: List[int], rowCosts: List[int], colCosts: List[int]) -> int:
        x1, y1 = startPos[0], startPos[1]
        x2, y2 = homePos[0], homePos[1]
        res = 0
        if x1 <=x2:
            for x in range(x1+1, x2+1):
                res += rowCosts[x]
        else:
            for x in range(x1-1, x2-1,-1):
                res += rowCosts[x]
        if y1<=y2:
            for y in range(y1+1, y2+1):
                res += colCosts[y]
        else:
            for y in range(y1-1, y2-1,-1):
                res += colCosts[y]

        return res





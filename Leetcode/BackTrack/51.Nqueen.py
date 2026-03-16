from typing import  List

class Solution:
    def solveNQueens(self, n: int) -> List[List[str]]:
        s = set()
        col = [0]*n
        res = []
        #[ 2  4 1 3]
        def valid(row, co) -> bool:
            for R in range(row):
                C = col[R]
                if R+C == row + co or R-C == row - co:
                    return False
            return True


        def backtrack(r,s):
            if r == n:
               res.append(['.'*(co)+'Q'+'.'*(n-co-1) for co in col])
               return

            for c in s:
                if valid(r,c):
                    col[r] = c
                    backtrack(r+1,s-{c})

        backtrack(0,set(range(n)))
        return res







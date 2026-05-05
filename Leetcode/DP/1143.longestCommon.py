from typing import List
from functools import cache
class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        m = len(text1)
        n = len(text2)
        @cache
        def dfs(i,j):
            '''

            :param i:
            :param j:
            :return:
            dfs(i,j) = max(dfs(i-1,j),dfs(i,j-1),dfs(i-1,j-1) if
            if same , 那么加一
            '''
            if i <0 or j<0 :
                return 0
            if text1[i] == text2[j]:
                return dfs(i-1,j-1)+1
            else:
                return max(dfs(i,j-1),dfs(i-1,j))
        f = [[0]*(n+1) for _ in range(m+1)]
        for i in range(1,m+1):
            for j in range(1,n+1):
                if text1[i-1] == text2[j-1]:
                    f[i][j] = f[i-1][j-1] + 1
                else:
                    f[i][j] = max(f[i-1][j], f[i][j-1])

        return f[m][n]
        # return dfs(m-1,n-1)
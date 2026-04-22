from typing import List
from functools import cache



class Solution:
    def minDistance(self, word1: str, word2: str) -> int:
        '''

        :param word1:
        :param word2:
        :return:
        '''
        n = len(word1)
        m = len(word2)

        @cache
        def dfs(i, j):
            '''
            单词w1[:i], w2[:j]需要返回的最小次数
            :param i:
            :param j:
            :return:
            一共三种，dfs(i-1,j),dfs(i,j-1),dfs(i-1,j-1)
            假设i比j长，那么对应插入2，删除2，替换2
            '''
            if i < 0: return j + 1
            if j < 0: return i + 1  #重点

            if word1[i]==word2[j]:
                return dfs(i-1, j-1)
            else:
                return min(dfs(i, j-1),dfs(i-1,j),dfs(i-1,j-1))+1


        f = [[0]*(m+1) for _ in range(n+1)]
        f[0] = list(range(m+1))
        for i ,x in enumerate(word1):
            f[i+1][0] = i+1
            for j,y in enumerate(word2):
                f[i+1][j+1] = f[i][j] if x == y else min(f[i][j+1],f[i+1][j],f[i][j])+1

        return f[n][m]
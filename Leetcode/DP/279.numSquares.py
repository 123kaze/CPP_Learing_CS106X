import math
from functools import lru_cache


class Solution:
    def numSquares(self, n: int) -> int:
        '''
        把 1,4,9,16,⋯ 这些完全平方数视作物品体积，物品价值都是
        1。由于每个数（物品）选的次数没有限制，所以本题是一道标准的完全背包问题
        :param n:
        :return:
        dfs(i,j) = min(dfs(i-1,j),min(dfs(i-1,j),dfs(i,j-i^2)+1))
        '''
        q = (math.sqrt(n))
        @lru_cache(None)
        def dfs(i,j):
            '''
            从前i个完全平方数中选择一些数字，满足元素和
            恰好等于j，最少要选择的数字
            :param i:
            :param j:
            :return:
            '''

import heapq
from math import inf
from typing import List
class Solution:
    def maximumAmount(self, coins: List[List[int]]) -> int:
        '''

        :param coins:
        :return:
        '''
        res = -inf
        path = []
        direction = [(1,0),(0,1)]
        m = len(coins)
        n = len(coins[0])
        def dfs(i,j):
            nonlocal res
            if i<0 or j<0:
                return
            if i==m or j==n:
                if (i == m and j == n - 1) or (j == n and i == m - 1):
                    s = sum(path)
                    smallest_list = heapq.nsmallest(2, path)
                    for num in smallest_list:
                        if num < 0:
                            s += -num
                    res = max(res, s)
                return

            if 0<=i<m and 0<=j<n:
                path.append(coins[i][j])
                for dx,dy in direction:
                    x = i+dx
                    y = j+dy
                    dfs(x,y)
                path.pop()

        dfs(0,0)
        return res



from typing import Optional,List
from functools import cache

def unbounded_knapsack(capacity: int,w:List[int],v:List[int]) -> int:
    n = len(w)
    @cache
    def dfs1(i,c):
        if i < 0:
            return 0
        if c < w[i]:
            return dfs1(i-1,c)
        return max(dfs1(i-1,c),dfs1(i,c-w[i])+v[i])
    return dfs1(n-1,capacity)


class Solution:
    def coinChange(self, coins: List[int], amount: int) -> int:
        '''
        :param coins:
        :param amount:
        :return:
        dfs(i,c) = min(dfs(i-1,c),dfs(i,c-w[i])+v[i])
        '''
        n = len(coins)
        @cache
        def dfs1(i,c):
            if i < 0:
                return 0 if c == 0 else inf
            if c < coins[i]:
                return dfs1(i-1,c)
            return min(dfs1(i-1,c),dfs1(i,c-coins[i])+1)
        coins.sort(reverse=True)
        f = [[inf]*(amount+1) for _ in range(n+1)]
        f[0][0] = 0
        for i in range(n):
            for c in range(amount+1):
                if c < coins[i]:
                    f[i+1][c] = f[i][c]
                else:
                    f[i+1][c] = min(f[i][c],f[i+1][c-coins[i]]+1)

        res = f[n][amount]
        return res if res != inf else -1


@cache
def dfs(i,c):
    '''
    dfs(i,c) = min(dfs(i-1,c),dfs(i,c-w[i])+v[i])
    :param i: index
    :param c: rest ca
    :return: min number of coins
    边界c = 0，i =0 return 0 else inf
    '''
    if i < 0:
        return 0 if c == 0 else inf
    if c < coins[i]:
        return dfs(i-1,c)
    return min(dfs(i-1,c),dfs(i,c - coins[i])+1)









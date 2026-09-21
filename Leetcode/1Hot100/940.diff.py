import sys
from functools import lru_cache


class Solution:
    def distinctSubseqII(self, s: str) -> int:
        n = len(s)
        mod = 10**9 + 7
        previous = [-1] * n
        last = {}

        for i, char in enumerate(s):
            previous[i] = last.get(char, -1)
            last[char] = i

        @lru_cache(None)
        def dfs(i):
            '''
            dfs(i) = 2 * dfs(i-1) - dfs(previous[i-1])
            :param i: current index
            :return: the number of distinct subsequences
            '''
            # Count distinct subsequences of s[:i], including the empty one.
            if i == 0:
                return 1

            result = 2 * dfs(i - 1)
            if previous[i - 1] != -1:
                result -= dfs(previous[i - 1])
            return result % mod

        return (dfs(n) - 1) % mod

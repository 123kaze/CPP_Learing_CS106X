from typing import List
from functools import cache
class Solution:
    def longestPalindrome(self, s: str) -> str:
        n = len(s)
        @cache
        def dfs(i,j):
            '''
            i-j 是不是回文串
            :param i:
            :param j:
            :return:true or false
            dfs(i,j) = dfs(i-1,j)  dfs(i,j-1)
            '''
            if i >= j:
                return True
            return  (s[i]==s[j]) and dfs(i+1,j-1)
        max_len = 1
        start = 0
        for i in range(n):
            for j in range(i + max_len, n): # 优化：只检查比当前最长串更长的子串
                if dfs(i, j):
                    max_len = j - i + 1
                    start = i

        return s[start: start + max_len]

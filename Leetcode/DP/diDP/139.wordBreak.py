from typing import List
from functools import cache



class Solution:
    def wordBreak(self, s: str, wordDict: List[str]) -> bool:
        n = len(s)
        words = set(wordDict)
        maxlen = max(map(len, wordDict))
        # @cache
        # def dfs(i)->bool:
        #     if i == 0:
        #         return True
        #     for j in range(i,max(-1,i-maxlen-1),-1):
        #         if s[j:i] in words and dfs(j):
        #             return True
        #
        #     return False
        f = [False] *(n+1)
        f[0] = True
        for i in range(1,n+1):
            for j in range(i,max(-1,i-1-maxlen),-1):
                if s[j:i] in words and f[j]:
                    f[i] = True

            f[i] = False if not f[i] else True
        return f[n]
from functools import lru_cache

class Solution:
    def countSubstrings(self, s: str) -> int:
        n = len(s)

        @lru_cache(maxsize=None)
        def dfs(i,j):
            '''
            dfs(i,j)=dfs(i+1,j-1) if s[i] == s[j] else False
            :param i:
            :param j:
            :return: 从i到j是否字符串
            '''
            if i >= j:
                return True
            if s[i] != s[j]:
                return False

            return dfs(i+1,j-1)
        res = 0
        for j in range(n):
            for i in range(j+1):
                cur = dfs(i,j)
                if cur:
                    res+=1

        return res

s = Solution()
print(s.countSubstrings("abc"))
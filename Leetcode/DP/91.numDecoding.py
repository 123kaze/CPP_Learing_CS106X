from functools import lru_cache

cache = lru_cache(maxsize=None)

class Solution:
    def numDecodings(self, s: str) -> int:
        decode = {str(i): chr(64 + i) for i in range(1, 27)}
        n = len(s)
        if n == 1:
            return 0
        @cache
        def dfs(i):
            '''
            dfs(i) = dfs(i-1)+dfs(i-2)
            :param i:
            :return:
            '''
            nums1 = nums2 = 0
            if i<0:
                return 0
            if i==0:
                return 1
            if s[i-1] in decode:
                nums1 = dfs(i-1)
            if s[i-2:i] in decode:
                nums2 = dfs(i-2)

            return nums1+nums2

        return dfs(n)






s = Solution()
print(s.numDecodings("12"))
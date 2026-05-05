from functools import cache
class Solution:
    def longestValidParentheses(self, s: str) -> int:
        n = len(s)
        stack = []
        # @cache
        # def dfs(i):
        isv = [False]*n

        for i,c in enumerate(s):
            if c == '(':
                stack.append(i)
            elif stack and c == ')':
                isv[i] = isv[stack.pop()] = True

        ans = cnt = 0
        for b in isv:
            if b:
                cnt += 1
                ans = max(ans, cnt)
            else:
                cnt = 0

        return ans

    def longestValidParentheses1(self, s: str) -> int:
        n = len(s)
        @cache
        def dfs(i):
            '''
            :param i: 最后的角标
            :return: 最长的长度
            dfs(i) =
            '''
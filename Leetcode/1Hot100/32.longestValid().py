class Solution:
    def longestValidParentheses(self, s: str) -> int:
        if len(s) == 0:
            return 0

        n = len(s)
        dp = [0]*(n+1)
        st = []
        res = 0
        for i,v in enumerate(s):
            if s[i] == '(':
                st.append(i)
                continue
            elif s[i] == ')' and st:
                top = st[-1]
                st.pop()
                dp[i] = i-top +1 +(dp[top-1] if top>0 else 0)

        return max(dp)

s = Solution()
print(s.longestValidParentheses("((()))"))
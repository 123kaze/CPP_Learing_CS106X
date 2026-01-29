class Solution:
    def isMatch(self, s: str, p: str) -> bool:
        n = len(s)
        m = len(p)
        
        # dp[i][j] 表示 s 的前 i 个字符与 p 的前 j 个字符是否匹配
        dp = [[False] * (m + 1) for _ in range(n + 1)]
        
        # 初始状态：空字符串与空模式匹配
        dp[0][0] = True

        # 处理空字符串与模式的匹配 (例如 s="", p="a*b*")
        for j in range(2, m + 1):
            if p[j-1] == '*':
                dp[0][j] = dp[0][j-2]
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if p[j-1] == '*':
                    # 情况 1: '*' 代表 0 次前面的字符，直接跳过 pattern 的前两个字符
                    match_zero = dp[i][j-2]
                    
                    # 情况 2: '*' 代表 1 次或多次前面的字符
                    # 必须满足：s 的当前字符匹配 p 在 '*' 之前的那个字符
                    match_one_or_more = (s[i-1] == p[j-2] or p[j-2] == '.') and dp[i-1][j]
                    
                    dp[i][j] = match_zero or match_one_or_more
                else:
                    # 如果当前字符匹配（或是 '.'），则取决于前一个状态
                    if s[i-1] == p[j-1] or p[j-1] == '.':
                        dp[i][j] = dp[i-1][j-1]

        return dp[n][m]





class Solution:
    def isMatch(self, s: str, p: str) -> bool:
        m = len(s)
        n = len(p)

        dp =[[False]*(n+1) for _ in range(m+1)]
        dp[0][0] = True

        for j in range(2,n+1):
            if p[j-1] =='*':
                dp[0][j] = dp[0][j-2]
        
        for i in range(1,m+1):
            for j in range(1,n+1):
                if p[j-1] =='*':
                    match1 = dp[i][j-2]
                    match_not_zero = (s[i-1] == p[j-2] or p[j-2] == '.') and dp[i-1][j]
                    mat2 = match1 or match_not_zero
                    dp [i][j] = mat2
                
                else:
                    if p[j-1] =='.' or p[j-1] == s[i-1]:
                        dp[i][j] = dp[i-1][j-1]
            
        return dp[m][n]
                    
from functools import cache

s = input()
q = len(s)
n = int(input())
dp = [0]*(n+1)
# dp[0] = 1
# dp[]
@cache
def dfs(i,remain):
    '''
    dfs(i,remain) = dfs(i+1,(remain*10+d)%n)
    '''
    if i>=q:
        return 1 if remain == 0 else 0
    ch = s[i]
    if ch != 'X':
        d = int(ch)
        return dfs(i+1,(remain*10+d)%n)
    res = 0
    if i == 0:
        for d in range(1,10):
            res += dfs(i+1,(remain*10+d)%n)
    else:
        for d in range(10):
            res += dfs(i+1,(remain*10+d)%n)
    return res

print(dfs(0,0))
        
        

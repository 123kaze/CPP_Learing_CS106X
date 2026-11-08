'''
易老师购买了一盒饼干，盒子中一共有k块饼干，但是数字k有些数位变得模糊了，看不清楚数字具体是多少。
易老师需要你帮忙把这k块饼干平分给n个小朋友，易老师保证这盒饼干能平分给n个小朋友。现在需要计算出k有多少种可能的数值。
输入格式:
输入包括两行，第1行为盒子上的数值k，模糊的数位用X表示，长度小于18（ 可能有多个模糊的数位），第2行为小朋友的人数n。
输出格式:
输出k可能的数值种数，保证至少为1。
'''
from functools import lru_cache,cache
k = input()
n = int(input())
q = len(k)
@cache
def dfs(i,remain):
    '''
    dfs(i,remain) = dfs(i+1,(remain*10+d)%n)
    '''
    if i>=q:
        return 1 if remain == 0 else 0
    ch = k[i]
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




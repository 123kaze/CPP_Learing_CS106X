# /*
# 7-64 至多删三个字符
# 分数 20
# 作者 曹鹏
# 单位 Google
# 给定一个全部由小写英文字母组成的字符串，允许你至多删掉其中 3 个字符，结果可能有多少种不同的字符串？

# 输入格式：
# 输入在一行中给出全部由小写英文字母组成的、长度在区间 [4, 10**6] 内的字符串。
# ababcc
# 输出格式：
# 在一行中输出至多删掉其中 3 个字符后不同字符串的个数。
# */
from functools import cache
import sys
sys.setrecursionlimit(100000)
s = input()
n = len(s)
last = [0]*(n+1)
k = 3
aa = {}
for i,c in enumerate(s,1):
    if c not in aa:
        last[i] = 0
        aa[c] = i
    else:
        last[i] = aa[c]
        aa[c] = i 
print(last)
@cache
def dfs(i,j):
    '''
    dfs(i,j) = dfs(i-1,j-1)+dfs(i-1,j) - dfs(p-1,j-(i-p))
    '''
    if (i<0 or j<0):
        return 0
    if (i==0 and j==0):
        return 1
    if last[i]>0 and (j-(i-last[i]))>= 0 :
        return dfs(i-1,j-1)+dfs(i-1,j) - dfs(last[i]-1,j-(i-last[i]))
    return dfs(i-1,j-1)+dfs(i-1,j)

print(sum(dfs(n,i) for i in range(4)))




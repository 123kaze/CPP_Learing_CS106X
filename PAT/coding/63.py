"""
韩梅梅喜欢满宇宙到处逛街。现在她逛到了一家火星店里，发现这家店有个特别的
规矩：你可以用任何星球的硬币付钱，但是绝不找零，当然也不能欠债。韩梅梅手边有
10^4 枚来自各个星球的硬币，需要请你帮她盘算一下，是否可能精确凑出要付的款额。

输入格式：
输入第一行给出两个正整数：N（≤ 10^4）是硬币的总个数，M（≤ 10^2）是韩梅梅要付的
款额。第二行给出 N 枚硬币的正整数面值。数字间以空格分隔。

输出格式：
在一行中输出硬币的面值 V_1 ≤ V_2 ≤ … ≤ V_k，满足条件
V_1 + V_2 + … + V_k = M。数字间以 1 个空格分隔，行首尾不得有多余空格。若解不唯一，
则输出最小序列。若无解，则输出 No Solution。

注：我们说序列 {A[1], A[2], …} 比 {B[1], B[2], …} “小”，是指存在 k ≥ 1，使得对所有
i < k 都有 A[i] = B[i]，并且 A[k] < B[k]。
"""
from functools import cache

n,m = map(int,input().split())
v = list(map(int,input().split()))
v.sort()
res = []
def dfs(i,space):
    '''
    dfs(i,s) = for j form i[dfs(j+1,space - v[j])]
    dfs(i, space) = 对所有 j ∈ [i, n)：
                    选择 v[j]
                    dfs(j + 1, space - v[j])
    '''
    if space == 0:
        return True

    for j in range(i,n):
        if v[j] > space:
            break
   
        res.append(v[j])

        if dfs(j+1,space - v[j]):
            return True

        res.pop()

    return False

if dfs(0,m):
    print(*res)
else:
    print("No Solution")
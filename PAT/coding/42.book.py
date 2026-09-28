"""分书问题。

给定 ``n`` 个人对 ``m`` 本书的喜好关系（``n <= m <= 8``），为每个人
分配一本其喜欢的书。每人恰好分到一本书，每本书至多分给一个人；列出所有
满足条件的分配方案。

输入：
    第一行包含正整数 ``n`` 和 ``m``，分别表示人数和书的数量。
    随后 ``n`` 行各包含 ``m`` 个 0 或 1：第 ``i`` 行第 ``j`` 列为 1 表示
    第 ``i`` 个人喜欢第 ``j`` 本书，0 表示不喜欢。

输出：
    按字典序升序输出所有方案 ``(s1, ..., sn)``，其中 ``si`` 表示第 ``i``
    个人分到的书号。

字典序：
    对方案 ``a`` 和 ``b``，若存在 ``k``，使得所有 ``i < k`` 均有
    ``a[i] == b[i]``，且 ``a[k] < b[k]``，则 ``a < b``。
"""
import sys
first_line = sys.stdin.buffer.readline().split()
if not first_line:
    sys.exit(0)
n ,m = map(int,first_line)
need = []
for i in range(n):
    need.append(list(map(int,input().split())))

res = []
visited = [False]*m
def dfs(i,path):
    '''
    dfs(i) = dfs(i-1)+cao
    '''
    if i>n-1:
        res.append("(" + ", ".join(map(str, path[:])) + ")")
        return
    for j,v in enumerate(need[i]):
        if v == 0:
            continue
        if visited[j]:
            continue
        visited[j] = True
        path.append(j+1)
        dfs(i+1,path)
        path.pop()
        visited[j] = False
dfs(0,[])

for num in res:
    print(num)


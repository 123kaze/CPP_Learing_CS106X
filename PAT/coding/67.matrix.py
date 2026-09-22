import sys
from functools import cache


sys.setrecursionlimit(5000)

n = int(input())
m = list(map(int, input().split()))

matrix = []
for i in range(n):
    matrix.append([m[i], m[i + 1]])

cut = [[0] * (n + 1) for _ in range(n + 1)]


@cache
def dfs(i, j):
    """Return the minimum multiplication cost for matrices i through j."""
    if i == j:
        return 0

    res = 999999
    for k in range(i, j):
        cost = dfs(i, k) + dfs(k + 1, j) + m[i - 1] * m[k] * m[j]
        if cost < res:
            res = cost
            cut[i][j] = k

    return res


@cache
def build(i, j):
    if i == j:
        return f"M{i}"

    k = cut[i][j]
    return "(" + build(i, k) + ")x(" + build(k + 1, j) + ")"


res = dfs(1, n)
print(build(1, n))
print(res)

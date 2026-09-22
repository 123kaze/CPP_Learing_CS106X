n, w = map(int, input().split())
wi = list(map(int, input().split()))
v = list(map(int, input().split()))

dp = [[0] * (w + 1) for _ in range(n + 1)]

for i in range(1, n + 1):
    weight = wi[i - 1]
    value = v[i - 1]

    prev = dp[i - 1]
    cur = dp[i]

    # 放不下当前物品的部分，直接复制
    cur[:weight] = prev[:weight]

    # 能放下当前物品的部分
    for space in range(weight, w + 1):
        no_choose = prev[space]
        choose = prev[space - weight] + value

        if choose > no_choose:
            cur[space] = choose
        else:
            cur[space] = no_choose


q = dp[n][w]

ans = [0] * n
space = w

for i in range(n, 0, -1):
    weight = wi[i - 1]
    value = v[i - 1]
    if (
        space >= weight
        and dp[i][space] == dp[i - 1][space - weight] + value
    ):
        ans[i - 1] = 1
        space -= weight

print(q)
print(*ans)
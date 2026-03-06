n, m, start, target = map(int, input().split())  # 改名为 start 和 target
teams = list(map(int, input().split()))

INF = float("inf")
graph = [[INF] * n for _ in range(n)]
for i in range(n):
    graph[i][i] = 0

for _ in range(m):
    u, v, l = map(int, input().split())  # 使用 u, v 代替 c1, c2
    graph[u][v] = l
    graph[v][u] = l

visited = [False] * n
dist = [INF] * n
pathCount = [0] * n
rescur = [0] * n

dist[start] = 0
pathCount[start] = 1
rescur[start] = teams[start]

for _ in range(n):
    # 找到未访问节点中距离最小的节点
    minDist = INF
    u = -1
    for i in range(n):
        if not visited[i] and dist[i] < minDist:
            minDist = dist[i]
            u = i

    if u == -1:
        break

    visited[u] = True
    # 更新 u 相邻节点
    for v in range(n):
        if not visited[v] and graph[u][v] != INF:
            if dist[u] + graph[u][v] < dist[v]:
                dist[v] = dist[u] + graph[u][v]
                pathCount[v] = pathCount[u]
                rescur[v] = rescur[u] + teams[v]
            elif dist[u] + graph[u][v] == dist[v]:
                pathCount[v] += pathCount[u]
                if rescur[u] + teams[v] > rescur[v]:
                    rescur[v] = rescur[u] + teams[v]

print(pathCount[target], rescur[target])  # 使用 target 而不是 c2

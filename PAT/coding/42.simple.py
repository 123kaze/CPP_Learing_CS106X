n,m = map(int,input().split())
visited = [False]*m
need = [list(map(int,input().split())) for _ in range(n)]
# print(need)
path = []

def dfs(i):
    if i==n:
        print('('+', '.join(map(str, path[:])) + ')')
        return
    for j in range(m):
        if need[i][j] == 1 and not visited[j]:
            path.append(j+1)
            visited[j] = True
            dfs(i+1)
            path.pop()
            visited[j] = False

dfs(0)
    
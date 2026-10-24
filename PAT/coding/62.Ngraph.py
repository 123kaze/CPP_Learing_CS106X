from collections import defaultdict
n  = int(input())
g = defaultdict(list)
visited = [0]*(n+1)

for i in range(1,n+1):
    s = input()
    for j in range(1,n+1):
        if s[j-1] == 'W':
            g[i].append(j)
        if s[j-1] == 'L':
            g[j].append(i)
for key,num in g.items():
    g[key] = sorted(num)
def dfs(node,path):
    if len(path) == n:
        if len(path) == n and 1 in g[node]:
            return path[:]
        return None
    for child in g[node]:
        if visited[child]:
            continue
        visited[child] = 1
        path.append(child)
        res = dfs(child,path)
        visited[child] = 0
        path.pop()
        if res is not None:
            return res
visited[1] = 1
res = dfs(1,[1])
if res:
    print(*res)
else:
    print('No Solution')

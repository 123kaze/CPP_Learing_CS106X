from collections import defaultdict,deque

n = int(input())
child = defaultdict(list)
indegree = defaultdict(int)
parent = [0]*(n+1)
for i in range(1,n+1):
    cur = list(map(int,input().split()))
    lens = cur[0]
    if lens ==0:
        continue
    child[i] = cur[1:]
    for v in cur[1:]:
        parent[v]+=1
print(parent)
root = 0
for v in range(1,n+1):
    if parent[v] ==0:
        root = v
        break
print(root)
target = 0
q = deque()
q.append(root)
depth = 0
while q:
    n = len(q)
    depth +=1
    target = q[0]
    print(q)
    for i in range(n):
        cur = q.popleft()
        for chil in child[cur]:
            q.append(chil)

print(target)





    


    


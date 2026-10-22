from collections import defaultdict,deque

n,m = map(int,input().split())

node = defaultdict(list)
olds = [None]*(n+1)
cnt = defaultdict(int)
parent = {}
names = set()

for _ in range(m):
    a,b = input().split()
    names.add(b)
    if a.isdigit():
        olds[int(a)] = b
        cnt[b] += 1
    else:
        names.add(a)
        parent[a] = b
        node[b].append(a)

order = [x for x in names if x not in parent]
q = deque(order)

while q:
    u = q.popleft()
    for v in node[u]:
        order.append(v)
        q.append(v)
    
for v in reversed(order):
    if v in parent:
        cnt[parent[v]]+=cnt[v]
def add(x, d):
    # 从结点 x 一路往上走到根，每个结点加 d
    while x is not None:
        cnt[x] += d
        x = parent.get(x)

while True:
    line = input().split()
    if not line or line[0] == 'E':
        break
    if line[0] == 'T':
        e, x = int(line[1]), line[2]
        if olds[e] is not None:
            add(olds[e], -1)
        olds[e] = x
        add(x, 1)
    elif line[0] == 'Q':
        print(cnt[line[1]])
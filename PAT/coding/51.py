from collections import deque,defaultdict

child = defaultdict(list)
cnt = defaultdict(int)
q = deque()
parent = defaultdict(int)
names = set()

n,m = map(int,input().split())
olds = [None]*(n+1)

for _ in range(m):
    a,b = input().split()
    names.add(b)
    if a.isdigit():
        olds[int(a)] = b
        cnt[b]+=1
    else:
        parent[a] = b
        child[b].append(a)
        names.add(a)
order = [x for x in names if x not in parent]
q = deque(order)

while q:
    u = q.popleft()
    for v in child[u]:
        order.append(v)
        q.append(v)
for u in reversed(order):
    if u in parent:
        cnt[parent[u]]+=cnt[u]
def add(x, d):
    '''
    给节点x增加d,以及他的父亲
    '''
    while x is not None:
        cnt[x] += d
        x = parent.get(x)

while True:
    line = input().split()
    if not line or line[0] == 'E':
        break
    if line[0] == 'T':
        old,node = int(line[1]),line[2]
        if olds[old] is not None:
            add(olds[old], -1)
        olds[old] = node
        add(node,1)
    elif line[0] == 'Q':
        print(cnt[line[1]])



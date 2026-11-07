import heapq
n, m, k = map(int, input().split())
res = []
qq = []
for i in range(n):
    cur = list(map(int, input().split()))
    res.append(cur)
    for j, v in enumerate(cur):
        qq.append((-v, i, j))
heapq.heapify(qq)
x1 = set()
y1 = set()
cnt = 0
while cnt < k:
    v, x, y = heapq.heappop(qq)
    if x in x1 or y in y1:
        continue
    x1.add(x)
    y1.add(y)
    cnt += 1
for i in range(n):
    if i in x1:
        continue
    print(*(res[i][j] for j in range(m) if j not in y1))
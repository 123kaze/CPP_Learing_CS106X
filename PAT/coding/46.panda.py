import heapq

def toSecond(s):
    h, m, c = map(int, s.split(':'))
    return (h*3600+m*60+c)

n = int(input())
data = []
for i in range(n):
    start,end = map(toSecond,input().split())
    data.append((start,end))
curr = 0
res = 0
data.sort(key=lambda x:(x[0],x[1]))
q = []
for start,end in data:
    while q and q[0] < start:
        heapq.heappop(q)
    heapq.heappush(q,end)
    res = max(len(q),res)

print(res)




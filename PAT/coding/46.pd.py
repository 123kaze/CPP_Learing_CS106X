events = []
def toSecond(s):
    h, m, c = map(int, s.split(':'))
    return (h*3600+m*60+c)
n = int(input())
for _ in range(n):
    start, end = input().split()
    events.append((toSecond(start), 1))
    events.append((toSecond(end), 0))

events.sort(key=lambda x: (x[0], -x[1]))

current = res = 0
for time,eve in events:
    if eve == 1:
        current+=1
        res = max(res,current)
    else:
        current-=1

print(res)

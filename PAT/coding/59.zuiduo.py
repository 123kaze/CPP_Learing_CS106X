import sys

n = int(sys.stdin.readline())
times = []
def mins(s):
    h,mi,sc = map(int,s.split(':'))
    return (h*3600+mi*60+sc)
for i in range(n):
    b = input().split()
    while not b:
        b = input().split()
    start, end = b
    begin = mins(start)
    ends = mins(end)
    times.append((begin,ends))

times.sort(key=lambda x:x[1])
res = 0
last = -1
for begin,end in times:
    if begin >= last:
        res+=1
        last = end

print(res)
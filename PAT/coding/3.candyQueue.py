from collections import deque


n,m = map(int,input().split())

q = deque(range(8))
count = 0
while n:
    qu = (n+m)//(m+1)
    n -= qu
    count+=1

print(count)


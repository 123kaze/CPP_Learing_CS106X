n = int(input())
from collections import Counter
m = list(map(int,input().split()))
c = Counter(m)
for num,val in sorted(c.items(),key = lambda x:x[0]):
    print(f'{num}:{val}')
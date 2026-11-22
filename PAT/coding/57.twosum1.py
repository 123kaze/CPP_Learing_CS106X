n,m = map(int,input().split())
dic = {}
s = set()
data = list(map(int,input().split()))
for num in data:
    if num >= m:
        continue
    if num in dic:
        s.add(num)
        s.add(m-num)
        continue
    dic[m-num] = num

print(*(x for x in data if x not in s),end=' ')


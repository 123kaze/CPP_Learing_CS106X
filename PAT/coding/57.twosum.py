n,m = map(int,input().split())
nums = list(map(int,input().split()))

dic = {}
s = set()
for num in nums:
    if num >= m:
        continue
    if num in dic:
        s.add(num)
        s.add(m-num)
        continue
    target = m-num
    dic[target] = num

print(*[i for i in nums if i not in s] ,end = ' ')
    
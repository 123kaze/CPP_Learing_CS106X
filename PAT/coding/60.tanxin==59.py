n = int(input())
starts = list(map(int,input().split()))
ends =  list(map(int,input().split()))
data = [(x,y) for x,y in zip(starts,ends)]
data.sort(key = lambda x:x[1])
res = 0
last = -1
for start,end in data:
    if start >= last:
        res+=1
        last = end

print(res)
n = int(input())
m = list(map(int,input().split()))

boxes = [100]*(n+1)
i = 0
res = [0]*(n+1)
for j in range(n):
    v = m[j]
    for i in range(n):
        if boxes[i]>=v:
            boxes[i]-=v
            res[j] = i
            break
while boxes[i]<100:
    i+=1
for v,j in zip(m,res):
    print(f'{v} {j+1}')
print(i)

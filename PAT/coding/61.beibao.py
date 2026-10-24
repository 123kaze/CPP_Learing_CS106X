n,W = map(float,input().split())
n = int(n)
w = list(map(float,input().split()))
v = list(map(float,input().split()))
data = [(wig,val,i) for wig,val,i in zip(w,v,list(range(n)))]
data.sort(key = lambda x:-x[1]/x[0])
t = W
i = 0
res = 0
index = set()
last = -1
q = 0
while t>0 and i<n:
    if t<data[i][0]:
        res+= data[i][1] * (t/data[i][0])
        q = t/data[i][0]
        last = data[i][2]
        break
    res+= data[i][1]
    t-=data[i][0]
    index.add(data[i][2])
    i+=1

print(f'{res:.2f}')
for i in range(n):
    if i in index:
        print(f'1.00',end = ' ')
    elif i==last:
        print(f'{q:.2f}',end = ' ')
    else:
        print(f'0.00',end = ' ')
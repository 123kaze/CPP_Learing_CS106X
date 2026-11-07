n,m = map(int,input().split())

sold = list(map(int,input().split()))
buy = list(map(int,input().split()))
res = 0
for i in range(m):
    opt,i,c = map(int,input().split())
    i-=1
    if opt == 1:
        res+=sold[i]*c
    else:
        res-=buy[i]*c
print(res)
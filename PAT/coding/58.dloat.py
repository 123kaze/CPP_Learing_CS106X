n,m = map(int,input().split())
size = list(map(float,input().split()))
val = list(map(float,input().split()))
s = sorted( zip(size,val),key = lambda x:-x[1]/x[0] if x[0] else float('-inf'))
res =0
for w,v in s:
    if m<=w:
        res += (m/w)*v
        m=0
        break
    res += v
    m -=w
print(f'{res:.2f}')
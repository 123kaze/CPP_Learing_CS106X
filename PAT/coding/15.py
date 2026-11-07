v,n = map(int,input().split())
data = []
for i in range(n):
    name,w,val = input().split()
    w = int(w)
    val = float(val)
    data.append([name,w,val])
data.sort(key = lambda x:x[2])
for name,wei,val in data:
    if wei<=v:
        print(f'{name} {wei} {val:.2f}')
        break
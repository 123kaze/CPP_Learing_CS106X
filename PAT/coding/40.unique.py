dic = set()
diclis = {}

init, n = input().split()
n = int(n)

for i in range(n):
    di, v, next = input().split()
    v = int(v)
    diclis[di] = (v, next)

node = []
delet1 = []

cur = init

while cur != '-1':
    curval = diclis[cur][0]
    nxt = diclis[cur][1]
    if abs(curval) not in dic:
        node.append(cur)
        dic.add(abs(curval))
    else:
        delet1.append(cur)
    cur = nxt

t = len(node)

for i, dis in enumerate(node):
    if i < t - 1:
        print(f'{dis} {diclis[dis][0]} {node[i+1]}')
    else:
        print(f'{dis} {diclis[dis][0]} -1')


t = len(delet1)

for i, dis in enumerate(delet1):
    if i < t - 1:
        print(f'{dis} {diclis[dis][0]} {delet1[i+1]}')
    else:
        print(f'{dis} {diclis[dis][0]} -1')
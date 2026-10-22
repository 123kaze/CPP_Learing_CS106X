from collections import defaultdict
n = int(input())
child = defaultdict(list)
par = {}
root = 0
for i in range(1,n+1):
    p = int(input())
    if p ==0:
        root = i
    par[i] = p
    child[p].append(i)
res = []
k = max(len(child[i]) for i in range(1,n+1))
def preorder(node):
    if child[node] == None:
        return
    res.append(node)
    for ch in child[node]:
        preorder(ch)
preorder(root)
if all(len(child[i]) == k or len(child[i]) == 0 for i in range(1,n+1)):
    flag = 'yes'
else:
    flag = 'no'
print(f'{k} {flag}')
print(*res)
    
from collections import defaultdict
n = int(input())
left = defaultdict(list)
type =  defaultdict(int)
right = defaultdict(list)
father = [0]*(n+1)

for i in range(1,n+1):
    y = list(map(int,input().split()))
    if len(y) == 3:
        t,l,r = y
    else:
        r= 0
        t,l = y
    type[i] = t
    left[i] = l
    right[i] = r
    father[l]= i
    father[r]=i
root = 0
for j in range(1,n+1):
    if father[j] == 0:
        root = j
        break

q = ''
qi = 0
def dfs(i):
    global qi
    if i ==0:
        s = (q[qi] == '1')
        qi+=1
        return s
    if type[i] == 1:
        a = dfs(left[i])
        b = dfs(right[i])
        return a and b # 小心python的提前结束
    elif type[i] == 2:
        a = dfs(left[i])
        b = dfs(right[i])
        return a or b
    else:
        return not dfs(left[i])
m = int(input())
for i in range(m):
    q = input()
    qi = 0
    if dfs(root):
        print('Ai')
    else:
        print('BuAi')

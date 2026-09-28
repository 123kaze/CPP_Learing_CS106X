from collections import defaultdict

n = int(input())
m = {}
gend = {}
for i in range(n):

    p = input().split()
    m[p[0]] = [p[1],p[2],p[3]]
    gend[p[0]] = p[1]
    gend[p[3]] = 'F'
    gend[p[2]] = 'M'
cache = {}
def get(pid):
    if pid in cache:
        return cache[pid]
    curlevel = {pid}
    ans = set()
    for g in range(5):
        ans.update(curlevel)
        if g == 4:
            break
        next = set()
        for p in curlevel:
            if p not in m:
                continue
            father = m[p][1]
            mother = m[p][2]
            if father != '-1':
                next.add(father)
            if mother != '-1':
                next.add(mother)
        curlevel = next
    cache[pid] = ans
    return ans


k = int(input())

for i in range(k):
    pid1,pid2 = input().split()
    gend1 = gend[pid1]
    gend2 =  gend[pid2]
    if gend1 == gend2:
        print('Never Mind')
        continue
    ans1 = get(pid1)
    ans2 = get(pid2)

    if ans1 & ans2:
        print('No')
    else:
        print('Yes')


"""五服以内不得通婚。
题目描述：
    两个人最近的共同祖先如果在五代以内，则不可通婚。五代包括本人、
    父母、祖父母、曾祖父母、高祖父母，即从本人开始最多向上追溯四次。
    给定血缘关系和若干对有情人的 ID，判断他们是否可以成婚。
输入格式：
    第一行给出正整数 N（2 <= N <= 10^4），表示人物信息的记录数。
    随后 N 行，每行给出：
        本人ID 性别 父亲ID 母亲ID
    ID 为 5 位数字，每人的 ID 不同；性别 M 表示男性，F 表示女性。
    如果父亲或母亲的身份不可考，相应的 ID 标记为 -1。
    接下来给出正整数 K，表示查询数。
    随后 K 行，每行给出一对有情人的 ID，以空格分隔。
输出格式：
    对每一对有情人输出一行判断结果：
    - 两人同性：输出 Never Mind。
    - 两人异性且关系已出五服：输出 Yes。
    - 两人异性且关系未出五服：输出 No。

题目保证：
    - 每对查询中的两个人是同辈。
    - 每人只有一个性别。
    - 血缘关系网中没有乱伦或隔辈成婚的情况。
"""

from collections import defaultdict
from functools import cache
n = int(input())
gend = {}
ids = {}
for i in range(n):
    cur = input().split()
    ids[cur[0]] = cur[1:]
    gend[ids[0]] = ids[1]
    gend[ids[3]] = 'F'
    gend[ids[2]] = 'M'

def canMarry(a,b):
    gend1 = gend[a]
    gend2 =  gend[b]
    if gend1 == gend2:
        print('Never Mind')
        return
    qin1 = get(a)
    qin2 = get(b)
    if qin1 & qin2:
        print('No')
    else:
        print('Yes')
    

def get(id):
    curlevel = {id}
    res = set()
    for g in range(5):
        res.update(curlevel)
        if g == 4:
            break

        next = set()
        for p in curlevel:
            father = ids[p][1]
            mother = ids[p][2]
            if father != '-1':
                next.add(father)
            if mother != '-1':
                next.add(mother)
        curlevel = next

    return res

k = int(input())
for i in range(k):
    a,b = input().split()
    canMarry(a,b)





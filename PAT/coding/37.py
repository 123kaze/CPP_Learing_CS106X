n = int(input())
def sumW(num):
    res = 0
    while num:
        d = num%10
        res+=d
        num = num//10
    return res
# print(sumW(123))
for i in range(n):
    cur = int(input())
    now = sumW(cur)
    flag = True
    for j in range(2,10):
        item = cur*j
        if (now != sumW(item)):
            flag = False
            print('NO')
            break
    if flag:
        print(now) 
        
    
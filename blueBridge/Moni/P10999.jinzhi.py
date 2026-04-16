res = 0
def JZ(x,n):
    ans = 0
    while x>0:
        num = x%n
        x//n
        ans += num
    return ans


for i in range(1, 2024):
    res += 1 if JZ(i,2) == JZ(i,4) else 0

print(res)
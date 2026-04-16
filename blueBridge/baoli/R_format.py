def round_half_up_int(x):
    import math
    if x >= 0:
        return math.floor(x + 0.5)
    else:
        return math.ceil(x - 0.5)   # 负数时：-2.5 -> -3

def solve():
    ans = 0
    n,d = map(float, input().split())
    ans = round_half_up_int(d*(2**n))
    print(ans)

solve()
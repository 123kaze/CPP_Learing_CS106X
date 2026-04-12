def check(n, x):
    temp = n
    while temp > 0:
        if temp % x > 9:  # 如果余数大于 9，说明会出现字母 (A-Z)
            return False
        temp //= x
    return True

n = 8100178706957568
for x in range(11, 37):
    if check(n, x):
        print(f"找到满足条件的进制 x = {x}")
from math import sqrt

print(sqrt(73851378887217385137888721*4+10470245))

def solve():
    target = 2024041331404202
    period = 200

    # 1. 处理特殊情况 i < 10 (B(i) 还没变成 100 的倍数)
    special_count = 0
    for i in range(1, 10):
        a_i = i * (i + 1) // 2
        b_i = 1
        for j in range(1, i + 1): b_i *= j
        if (a_i - b_i) % 100 == 0:
            special_count += 1

    # 2. 处理 i >= 10 的情况 (此时 B(i) % 100 == 0)
    # 寻找满足 i(i+1) % 200 == 0 的 i (在一个周期 200 内)
    valid_in_period = []
    for i in range(period):
        if (i * (i + 1)) % 200 == 0:
            valid_in_period.append(i)

    # 统计 i >= 10 且 i <= target 的数量
    def count_in_range(limit):
        if limit < 10: return 0

        # 完整的周期数
        num_periods = (limit - 10 + 1) // period
        total = num_periods * len(valid_in_period)

        # 剩余不足一个周期的部分
        remainder_start = 10 + num_periods * period
        for i in range(remainder_start, limit + 1):
            if (i * (i + 1)) % 200 == 0:
                total += 1
        return total

    result = special_count + count_in_range(target)
    return result

print(f"符合条件的 i 的个数为: {solve()}")

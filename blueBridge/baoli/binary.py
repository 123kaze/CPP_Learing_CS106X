from math import comb

def count_balanced(n, length):
    """计算小于等于 n 且二进制长度为 length 的均衡数数量"""
    if n < 0: return 0
    s = bin(n)[2:]
    if len(s) < length: return 0
    if len(s) > length:
        # 如果 n 的位数超过目标位数，说明所有该位数的均衡数都小于 n
        return comb(length - 1, length // 2)

    # 相同位数，从高位向低位扫描
    count = 0
    ones_needed = length // 2
    ones_used = 0

    for i in range(length):
        if s[i] == '1':
            # 如果当前位是 1，尝试把这一位填 0，后面剩下的位随意填
            remaining_len = length - 1 - i
            remaining_ones = ones_needed - ones_used
            if remaining_ones >= 0:
                count += comb(remaining_len, remaining_ones)
            ones_used += 1

        if ones_used > ones_needed: break
    else:
        # 检查 n 自身是否为均衡数
        if ones_used == ones_needed:
            count += 1
    return count

def solve():
    target = 2026202620262026
    # 查找 50 位和 52 位中最接近 target 的数
    # 由于 50 位数一定小于 target，52 位数一定大于 target
    # 我们只需找 50 位中最大的和 52 位中最小的

    # 1. 50位最大的均衡数 (25个1, 25个0)
    max_50 = int('1'*25 + '0'*25, 2)

    # 2. 52位最小的均衡数 (1个1, 26个0, 25个1)
    min_52 = int('1' + '0'*26 + '1'*25, 2)
    # 计算差值
    diff_max_50 = abs(target - max_50)
    diff_min_52 = abs(target - min_52)

    if diff_max_50 <= diff_min_52:
        print(f"最近的均衡数是 (50位): {max_50}")
    else:
        print(f"最近的均衡数是 (52位): {min_52}")

if __name__ == "__main__":
    solve()

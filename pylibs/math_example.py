"""
@file math_example.py
@brief Python math 用法示例：算法题中的整数数学

特点与复杂度：
1. gcd 使用整数运算；lcm 可通过 gcd 计算。
2. isqrt 返回精确的整数平方根，避免浮点精度问题。
3. comb / perm / factorial 返回精确整数，但结果可能很大。
4. 辗转相除求 gcd 为 O(log(min(a,b))) 次取模；本示例试除判素数 O(sqrt(n))。
5. Python 大整数不溢出，但运算时间、空间会随位数增加。
"""

import math


def lcm(a, b):
    """最小公倍数；兼容没有 math.lcm 的 Python 3.8，含零时返回 0。"""
    if a == 0 or b == 0:
        return 0
    return abs(a // math.gcd(a, b) * b)


def is_prime(n):
    """试除法判断素数，适合单次且范围不大的查询。"""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    for divisor in range(3, math.isqrt(n) + 1, 2):
        if n % divisor == 0:
            return False
    return True


def main():
    print("========== Python math 用法示例 ==========")

    # 1. 最大公约数和最小公倍数
    print("\n1. gcd 和 lcm:")
    print(f"gcd(18, 24): {math.gcd(18, 24)}")
    print(f"lcm(18, 24): {lcm(18, 24)}")
    print(f"gcd(0, 12): {math.gcd(0, 12)}, lcm(0, 12): {lcm(0, 12)}")

    # 2. 精确整数开方
    print("\n2. isqrt 和完全平方数:")
    n = 10**30 + 1
    root = math.isqrt(n)
    print(f"n={n}, 向下取整的整数平方根: {root}")
    print(f"是否完全平方数: {root * root == n}")

    # 3. 组合数、排列数和阶乘
    print("\n3. 组合数、排列数和阶乘:")
    print(f"C(5, 2): {math.comb(5, 2)}")
    print(f"P(5, 2): {math.perm(5, 2)}")
    print(f"5!: {math.factorial(5)}")
    print(f"连乘 [2, 3, 4]: {math.prod([2, 3, 4])}")

    # 4. 取整与整数除法
    print("\n4. 取整和整数除法:")
    print(f"floor(-1.2): {math.floor(-1.2)}, ceil(-1.2): {math.ceil(-1.2)}")
    n, group_size = 8, 3
    print(f"8 个元素每组 3 个，需要组数: {(n + group_size - 1) // group_size}")
    print(f"整数除法向下取整 -7 // 3: {-7 // 3}")
    a, b = -7, 3
    print(f"整数除法向上取整，b>0 时用 -(-a // b): {-(-a // b)}")
    print(f"divmod(17, 5) 同时取商和余数: {divmod(17, 5)}")

    # 5. 算法应用
    print("\n5. 算法题应用:")
    numerator, denominator = 42, 56
    divisor = math.gcd(numerator, denominator)
    print(f"分数约分 42/56: {numerator // divisor}/{denominator // divisor}")
    print(f"不考虑障碍的 3x4 网格路径数: {math.comb(3 + 4 - 2, 3 - 1)}")
    print(f"1..20 内素数: {[x for x in range(1, 21) if is_prime(x)]}")
    print(f"三参数内置 pow(2, 100, 1000000007): {pow(2, 100, 1000000007)}")

    # 6. 易错点
    print("\n6. 易错点:")
    print("1. 大整数开方用 isqrt，避免 int(sqrt(n)) 的浮点误差")
    print("2. 模幂用内置 pow(a, b, mod)，不要用返回浮点数的 math.pow")
    print("3. comb / perm 不自动取模，超大规模取模组合数需专用算法")
    print("4. 大批量判断素数通常用筛法，不要对每个数重复试除")
    print("\n========== math 示例结束 ==========")


if __name__ == "__main__":
    main()

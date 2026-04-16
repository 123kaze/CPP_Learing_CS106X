import functools
import sys

# 限制 int 到 字符串转换的上限（防止 Python 3.10.7+ 的安全机制报错）
sys.set_int_max_str_digits(1000000)
def solve():
    n = int(sys.stdin.readline())
    nums = [bin(i)[2:] for i in range(1,n+1)]
    print(nums)
    nums.sort(key = functools.cmp_to_key(lambda a,b: 1 if a+b < b+a else -1))
    print(int("".join(nums),2))


if __name__ == '__main__':
    solve()
import sys

def solve():
    # 1. 预处理：统计每个数中 '6' 的个数
    input_data = sys.stdin.read().split()
    if not input_data: return
    n = int(input_data[0])
    nums = input_data[1:]

    ans = 0
    cnt = [0] * 6  # 记录含有 0-5 个 '6' 的数字数量

    for s in nums:
        count6 = s.count('6')
        if count6 >= 6:
            ans += 1  # 本身就是好数，直接加
        else:
            cnt[count6] += 1

    # 2. 贪心策略：优先两两组合 (2个数凑成 >= 6)
    # 5 可以搭配 1, 2, 3, 4, 5
    for i in range(5, 0, -1):
        # 5+1, 5+2... 4+2, 4+3... 3+3
        for j in range(1, 6):
            if i + j >= 6 and i >= j:
                if i == j:
                    pairs = cnt[i] // 2
                else:
                    pairs = min(cnt[i], cnt[j])

                ans += pairs
                cnt[i] -= pairs
                cnt[j] -= pairs

    # 3. 贪心策略：剩下的尝试三三组合 (3个数凑成 >= 6)
    # 此时剩下的数两两相加都小于 6，只能靠 3 个数凑
    # 暴力枚举所有三数组合 i+j+k >= 6
    for i in range(5, 0, -1):
        for j in range(i, 0, -1):
            for k in range(j, 0, -1):
                if i + j + k >= 6:
                    # 统计这组组合里每个数字需要的个数
                    needed = {}
                    for x in [i, j, k]:
                        needed[x] = needed.get(x, 0) + 1

                    # 计算当前能凑出多少组
                    can_make = 10**18
                    for x, num in needed.items():
                        can_make = min(can_make, cnt[x] // num)

                    if can_make > 0:
                        ans += can_make
                        for x, num in needed.items():
                            cnt[x] -= can_make * num

    print(ans)

if __name__ == "__main__":
    solve()
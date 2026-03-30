from collections import Counter

k = int(input())
s = input().strip()
n = len(s)

if n % k != 0:
    print(-1)
else:
    length = n // k
    res = 0

    for i in range(length):
        chars = [s[i + j * length] for j in range(k)]
        cnt = Counter(chars)
        max_cnt = max(cnt.values())
        res += k - max_cnt

    print(res)


from collections import Counter
import sys

def solve():
    try:
        line1 = sys.stdin.readline().strip()
        if not line1: return
        k = int(line1)
        s = sys.stdin.readline().strip()
    except EOFError:
        return

    n = len(s)

    # 如果长度不能被 k 整除，显然无法变成 k 次重复字符串
    if n % k != 0:
        print(-1)
        return

    L = n // k  # 每一个重复单元的长度
    ans = 0

    # 遍历重复单元的每一个位置 i (0 到 L-1)
    for i in range(L):
        cnt = Counter()
        # 统计在所有 k 个段中，第 i 个位置出现的字符频率
        for j in range(k):
            # 第 j 个段的第 i 个字符下标是 j * L + i
            char = s[j * L + i]
            cnt[char] += 1

        # 为了使这 k 个字符相同，保留出现次数最多的，修改其他的
        max_v = max(cnt.values())
        ans += (k - max_v)

    print(ans)

solve()
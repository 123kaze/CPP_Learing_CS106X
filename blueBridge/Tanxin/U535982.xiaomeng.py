'''
1. 逻辑拆解（纸上谈兵）目标状态：长度为 $2n$，
A 和 B 各占 $n$ 个，且相邻字符不同。
满足这个条件的字符串只有两种可能：ABAB...AB
(以 A 开头)BABA...BA (以 B 开头)操作本质：题目问“最少交换次数”。
底层规律：如果你有两个位置放错了（比如该放 A 的地方放了 B，该放 B 的地方放了 A），
你只需要 1 次交换 就能把这两个位置同时修正。
公式：最少交换次数 = $\frac{\text{放错位置的字符总数}}{2}$。
'''
def solve(s,n):
    import sys
    # 假设输入 n 和字符串 s
    # s = "AABB", n = 2

    # 情况 1: 目标是 ABAB...
    target1 = "AB" * n
    diff1 = 0
    for i in range(2 * n):
        if s[i] != target1[i]:
            diff1 += 1

    # 情况 2: 目标是 BABA...
    target2 = "BA" * n
    diff2 = 0
    for i in range(2 * n):
        if s[i] != target2[i]:
            diff2 += 1

    # 最终答案是两种目标的最小代价
    # 注意：每次交换修好 2 个错位，所以除以 2
    print(min(diff1, diff2) // 2)
T=int(input().strip())
for _ in range(T):
    n = int(input().strip())
    s = input().strip()
    solve(s,n)

dic = {
    0:6,
    1:2,
    2:5,
    3:5,
    4:4,
    5:5,
    6:6,
    7:3,
    8:7,
    9:6
}
n = int(input())
n -=4
def cost(x):
    return sum(dic[int(i)] for i in str(x))
cnt = [cost(i) for i in range(2000)]
nums = [i for i in range(1000) if cnt[i] <= n - 4]
res = 0
for a in nums:
    for b in nums:
        c = a + b
        if cnt[a] + cnt[b] + cnt[c] == n:
            res += 1

print(res)
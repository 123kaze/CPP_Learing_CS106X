import sys
input = sys.stdin.readline

n = int(input())
st = [False] * (n + 1)
cnt = 0

for i in range(2, n + 1):
    if not st[i]:
        cnt += 1
        for j in range(i + i, n + 1, i):
            st[j] = True

print(cnt)
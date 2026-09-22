n = int(input())
nums = []
for i in range(n):
    nums.append(input().strip())
res = []
for s in nums:
    res.append(sum(map(int,s[:3]))==sum(map(int,s[3:])))
for b in res:
    if b:
        print("You are lucky!")
    else:
        print("Wish you good luck.")
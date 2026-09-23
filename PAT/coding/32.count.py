from collections import Counter

n = input()
c = Counter(n)
res = [0]*10
for num,v in c.items():
    res[int(num)] = v

for i in range(10):
    if res[i] >0:
        print(f'{i}:{res[i]}')
        
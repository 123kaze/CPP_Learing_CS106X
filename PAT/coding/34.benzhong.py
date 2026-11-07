data = list(map(int,input().split()))
s = set(range(24))
while True:
    n = int(input())
    if n not in s:
        break
    v = data[n]
    if v>50:
        print(f'{v} Yes')
    else:
        print(f'{v} No')
    
s = input()
a = list(map(int, input().split()))
c= [s.count(chr(i + 97)) for i in range(26)]
print(*c)
print(sum(c[i]*a[i] for i in range(26)))
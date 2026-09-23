import statistics

n = int(input())
m = list(map(int,input().split()))

print(f'{statistics.variance(m):.2f}')


s = sum(m)/n
va = 0
for i in range(n):
    va+=(m[i]-s)**2

va = va/(n-1)
print(f'{va:.2f}')


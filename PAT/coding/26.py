# 1 3 5 7 2n-1。    2* t**2 -1 = x
# 3 5 7

import math

n,c = input().split()
n = int(n)
ta = i = 0
while ta<n:
    i+=1
    ta = 2*(i**2)-1

for j in range(i-1,0,-1):
    print(' '*((2*(i-1)-1 - (2*j-1))//2)+c*(2*j-1))

for j in range(2,i):
    print(' '*((2*(i-1)-1 - (2*j-1))//2)+c*(2*j-1))


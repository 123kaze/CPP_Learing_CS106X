
def check(x):
    cnt = 1
    while x:
        t = x%10
        if cnt %2 == 1:
            if not t%2:
                return False
        else:
            if t%2:
                return False
        x//= 10
        cnt += 1
    return True


def solve():
    ans = 0
    n = int(input())
    for i in range(1,n+1):
        if check(i):
            ans +=1
    print(ans)
solve()
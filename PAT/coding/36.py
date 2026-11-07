# 1.如果一位艺人的观众票数高，且得到至少 1 名评委的认可，该艺人就胜出
# 2.或艺人的观众票数低，但得到全部评委的认可，也可以胜出。
# 3.节目保证投票的观众人数为奇数，所以不存在平票的情况。

a,b = map(int,input().split())
ping = list(map(int,input().split()))

def checkA(a,b):
    if (a>b and any(p ==0 for p in ping)) or (all(p ==0 for p in ping)):
        return True
    return False

if checkA(a,b):
    t = ping.count(0)
    print(f'The winner is a: {a} + {t}')
else:
    t = ping.count(1)
    print(f'The winner is b: {b} + {t}')
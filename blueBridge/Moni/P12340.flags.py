from collections import Counter,deque
def solve():
    h,w = map(int,input().split())
    s = 'LANQIAO'
    base = s * ((w + h) // 7 + 2)
    res = 0

    for i in range(h):
        current = base[i:i+w]
        res+=Counter(current)["A"]


    print(res)

if __name__ == '__main__':
    solve()




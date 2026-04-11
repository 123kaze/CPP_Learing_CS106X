h,w = map(int, input().split())
def solve():
    minl = h+w -1
    s = '2025'*((minl+4-1) // 4)
    rows = []
    for i in range(min(h,4)):
        rows.append(s[i:i+w])
    for i in range(h):
        print(''.join(rows[i%4]))
if __name__ == '__main__':
    solve()
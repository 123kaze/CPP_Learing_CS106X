def main():
    n = int(input())
    if n==0:
        q = 0.00
        cout = 0
        print(f'average = {q:.2f}')
        print(f'count = {cout}')
        return
    
    m = []
    while len(m) < n:
        m.extend(map(int, input().split())) # 注意这里说的是可以用回车来隔断
    q = sum(m)/n
    cout = 0
    for i in m:
        cout += 1 if i>=60 else 0
    
    print(f'average = {q:.2f}')
    print(f'count = {cout}')

main()
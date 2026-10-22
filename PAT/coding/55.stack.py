n,m = map(int,input().split())
for _ in range(n):
    s = input()
    stack = []
    error = None
    for op in s:
        if op == 'S':
            stack.append('S')
            if len(stack) > m:
                error = 'NO'
                break
        if op == 'X':
            if not stack:
                error = 'NO'
                break
            stack.pop()
    if stack:
        error = 'NO'
    if error:
        print(error)
    else:
        print('YES')
            
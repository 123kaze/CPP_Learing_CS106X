stack = []
pairs = {')': '(', ']': '[', '}': '{', '*/': '/*'}
error = None

while True:
    line = input()
    if line =='.':
        break
    i = 0
    while i<len(line):
        if line[i:i+2] == '/*':
            stack.append('/*')
            i += 2
        elif line[i:i+2] == '*/':
            if not stack:
                error = '?-*/'
                break
            if stack[-1] != '/*':
                error = stack[-1] + '-?'
                break
            stack.pop()
            i += 2
        elif line[i] in '([{':
            stack.append(line[i])
            i+=1
        elif line[i] in ')]}':
            if not stack:
                error = '?-' + line[i]
                break
            if stack[-1] != pairs[line[i]]:
                error = stack[-1] + '-?'
                break
            i+=1
            stack.pop()
        else:
            i+=1
    if error:
        break

if error:
    print('NO')
    print(error)
elif stack:
    print('NO')
    print(stack[-1]+'-?')
else:
    print('YES')
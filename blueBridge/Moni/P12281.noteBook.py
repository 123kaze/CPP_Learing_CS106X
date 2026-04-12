import sys
T = int(input())
command = []
for _ in range(T):
    command.append(input().strip())
def solve():
    if not command:
        return
    pos = 0
    content = ''
    for c in command:
        if c.startswith('insert'):
            text = c[c.find('"')+1 : c.rfind('"')]
            content = content[:pos] + text + content[pos:]
            pos += len(text)
        elif c.endswith('h'):
            if c.startswith('d'):
                n = int(c[1:-1])
                start = max(0, pos - n)
                content = content[:start]+content[pos:]
                pos = start
            else:
                n = int(c[:-1])
                pos = max(0,pos -n)
        elif c.endswith('l'):
            if c.startswith('d'):
                n = int(c[1:-1])
                content = content[:pos] + content[pos+n:]
            else:
                n = int(c[:-1])
                pos = min(len(content), pos + n)

    print(content)
solve()


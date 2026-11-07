def main():
    a,b = input().split(' ',1)
    flag1 = False
    flag2 = False
    if a.isdigit() and 0<int(a)<=1000:
        a = int(a)
        print(f'{a} + ',end = '')
        flag1 = True
    else:
        print(f'? + ',end = '')

    if b.isdigit() and 0<int(b)<=1000:
        b = int(b)
        print(f'{b}',end = '')
        flag2 = True
    else:
        print(f'?',end = '')
    
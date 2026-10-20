w,h = map(float,input().split())
bmi = w/(h**2)
print(f'{bmi:.1f}')
if bmi >25:
    print('PANG')
else:
    print('Hai Xing')


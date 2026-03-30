n = int(input())
length = len(str(n))
if n == 10 ** (length - 1):
    print(n)
else:
    print(10 ** length)
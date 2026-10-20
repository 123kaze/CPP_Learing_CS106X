n = int(input())
def os(s):
    if "shinto mekkaku" in s:
        return True
    return False
for i in range(n):
    s = input().lower()
    if not os(s):
        print('Bonnjinn')
    else:
        print('Medaka Kuroiwa')
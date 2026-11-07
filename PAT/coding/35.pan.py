def islen(s):
    return len(s) >= 6
def charValid(s):
    return all(c.isascii() and (c.isalnum() or c == '.') for c in s)
def hasDigit(s):
    return any(c.isdigit() for c in s)
def hasLetter(s):
    return any(c.isalpha() for c in s)
def main():
    n = int(input())
    for i in range(n):
        s = input()
        if not islen(s):
            print('Your password is tai duan le.')
        elif not charValid(s):
            print('Your password is tai luan le.')
        elif not hasDigit(s):
            print('Your password needs shu zi.')
        elif not hasLetter(s):
            print('Your password needs zi mu.')
        else:
            print('Your password is wan mei.')

main()
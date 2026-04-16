import sys
n,k = map(int, sys.stdin.readline().split())
nums = list(map(int, sys.stdin.readline().split()))
nums.append(0)
maxa = max(nums)
def check(i):
    num1 = nums[:]
    for j in range(n):
        if num1[j] >i:
            if j+k <n:
                num1[j+k] = num1[j+k] +num1[j] - i
        else:
            return False
    return True

def solve():
    for i in range(1,maxa+1):
        if not check(i):
            print(i-1)
            break

if __name__ == "__main__":
    solve()
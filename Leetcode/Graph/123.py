def get_balance(s):
    diff = 0
    count_0 = 0
    count_1 = 0
    for char in s:
        if char == '0':
            diff -= count_1
            count_0 += 1
        else:
            diff += count_0
            count_1 += 1
    return diff

def solve():
    n = int(input().strip())

    s_list = list(input().strip())

    l, r = map(int, input().split())
    l, r = l - 1, r - 1

    left_part = s_list[:l]
    right_part = s_list[r+1:]
    m = r - l + 1

    for k in range(m + 1):
        fill_left = ['1'] * k + ['0'] * (m - k)
        str_left = left_part + fill_left + right_part
        diff_left = get_balance(str_left)

        fill_right = ['0'] * (m - k) + ['1'] * k
        str_right = left_part + fill_right + right_part
        diff_right = get_balance(str_right)
        if diff_left * diff_right <= 0:
            print("Yes")
            return

    print("No")

if __name__ == "__main__":
    t = int(input().strip())
    for _ in range(t):
        solve()
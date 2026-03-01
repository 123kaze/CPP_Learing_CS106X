a, b = map(int, input().split())
sum_num = a + b
print(f"{sum_num:,}")


# 方法1：直接实现
def format_number(num):
    # 处理负数
    if num < 0:
        return "-" + format_number(-num)

    # 转换为字符串
    s = str(num)
    result = []

    # 从后往前每三位加一个逗号
    for i in range(len(s) - 1, -1, -3):
        if i < 3:  # 处理最前面的部分
            result.insert(0, s[: i + 1])
        else:
            result.insert(0, s[i - 2 : i + 1])

    return ",".join(result)


a, b = map(int, input().split())
sum_num = a + b

# 输出结果
print(format_number(sum_num))

"""
中缀表达式转后缀表达式（逆波兰表示法）算法实现

简介：
这个程序实现了将中缀表达式转换为后缀表达式的算法，也称为逆波兰表示法（RPN）。
算法使用栈来处理运算符优先级，支持加减乘除四则运算、括号、负数和小数。

算法原理：
1. 从左到右扫描中缀表达式
2. 遇到操作数（数字）直接输出到结果
3. 遇到左括号压入栈
4. 遇到右括号，将栈顶元素弹出并输出直到遇到左括号
5. 遇到运算符，比较与栈顶运算符的优先级：
   - 如果栈为空或栈顶为左括号，直接压栈
   - 如果优先级高于栈顶运算符，压栈
   - 如果优先级不高于栈顶运算符，弹出栈顶并输出，然后比较新的栈顶
6. 扫描结束后，将栈中剩余运算符全部弹出并输出

特殊处理：
- 负数处理：当遇到减号且前面是左括号或表达式开头时，将其视为负号而不是减号
- 小数处理：支持小数点连接数字
- 使用特殊标记 '@' 表示一元负号

输入格式：一行中缀表达式，如 "3+4*(2-1)/5"
输出格式：后缀表达式，空格分隔，如 "3 4 2 1 - * 5 / +"
"""

import sys

# 快速输入函数，从标准输入读取一行并去除首尾空白
input = lambda: sys.stdin.readline().strip()

# 运算符优先级字典，数值越高优先级越高
priority = {"+": 1, "-": 1, "*": 2, "/": 2}

# 运算符栈
stack = []

# 读取中缀表达式
expression = input()

# 存储后缀表达式结果
result = []

# 当前扫描位置
i = 0

# 主循环：扫描中缀表达式
while i < len(expression):
    char = expression[i]

    # 情况1：当前字符是数字或小数点（操作数）
    if char.isdigit() or char == ".":

        # 处理负数：如果当前数字前有减号，且减号前是左括号或表达式开头
        # 例如：(-3) 或 -3+5 中的 -3
        if (
            i > 0
            and expression[i - 1] == "-"
            and (i == 1 or expression[i - 2] in ["(", "+", "-", "*", "/"])
        ):
            # 将负号与数字合并
            number = "-" + char

            # 如果栈顶是减号，弹出（因为减号已作为负号处理）
            if stack and stack[-1] == "-":
                stack.pop()
        else:
            # 正常数字
            number = char

        # 处理多位数和小数：继续读取后续的数字和小数点
        while i + 1 < len(expression) and (
            expression[i + 1].isdigit() or expression[i + 1] == "."
        ):
            i += 1
            number += expression[i]

        # 将完整的数字添加到结果中
        result.append(number)

    # 情况2：左括号，直接压栈
    elif char == "(":
        stack.append(char)

    # 情况3：右括号，弹出栈中元素直到遇到左括号
    elif char == ")":
        while stack and stack[-1] != "(":
            # 注意：这里没有处理一元负号标记 '@' 的特殊情况
            # 如果栈顶是 '@'，应该输出 '-' 而不是 '@'
            # 这是原代码的一个缺陷
            result.append(stack.pop())
        # 弹出左括号（不添加到结果）
        if stack:
            stack.pop()

    # 情况4：运算符（加减乘除）
    elif char in priority:

        # 处理一元运算符（正号、负号）
        if char in ["+", "-"] and (
            i == 0 or expression[i - 1] in ["(", "+", "-", "*", "/"]
        ):
            # 如果是负号，用特殊标记 '@' 表示一元负号
            if char == "-":
                stack.append("@")
        else:
            # 处理二元运算符
            # 当栈不为空，栈顶不是左括号，且栈顶运算符优先级不低于当前运算符时
            while (
                stack
                and stack[-1] != "("
                and priority.get(stack[-1], 0) >= priority.get(char, 0)
            ):
                # 如果栈顶是一元负号标记 '@'，输出负号
                if stack[-1] == "@":
                    result.append("-")
                else:
                    # 否则输出栈顶运算符
                    result.append(stack.pop())
                # 如果弹出后栈顶是 '@'，也弹出（处理连续一元负号）
                stack.pop() if stack and stack[-1] == "@" else None

            # 当前运算符压栈
            stack.append(char)

    # 移动到下一个字符
    i += 1

# 扫描结束后，将栈中剩余运算符全部弹出
while stack:
    # 处理一元负号标记
    if stack[-1] == "@":
        result.append("-")
    else:
        result.append(stack.pop())
    # 如果弹出后栈顶是 '@'，也弹出
    stack.pop() if stack and stack[-1] == "@" else None
# 输出后缀表达式，空格分隔
print(" ".join(result))

"""
示例运行：
输入：3+4*(2-1)/5
输出：3 4 2 1 - * 5 / +

输入：-3+5*(-2)
输出：-3 5 -2 @ * +  (注意：包含 '@' 是因为代码在处理右括号时没有特殊处理一元负号标记)

输入：(3.14+2.86)*4/2
输出：3.14 2.86 + 4 * 2 /

已知问题：
1. 在处理右括号时，如果栈顶是一元负号标记 '@'，会直接输出 '@' 而不是转换为 '-'
2. 对于表达式如 "-3+5*(-2)"，输出会包含 '@' 标记
"""

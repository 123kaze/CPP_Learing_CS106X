import sys

input = lambda: sys.stdin.readline().strip()


priority = {"+": 1, "-": 1, "*": 2, "/": 2}
stack = []
expression = input()
result = []

i = 0
while i < len(expression):
    char = expression[i]
    if char.isdigit() or char == ".":

        if (
            i > 0
            and expression[i - 1] == "-"
            and (i == 1 or expression[i - 2] in ["(", "+", "-", "*", "/"])
        ):
            number = "-" + char

            if stack and stack[-1] == "-":
                stack.pop()
        else:
            number = char

        while i + 1 < len(expression) and (
            expression[i + 1].isdigit() or expression[i + 1] == "."
        ):
            i += 1
            number += expression[i]

        result.append(number)

    elif char == "(":
        stack.append(char)

    elif char == ")":
        while stack and stack[-1] != "(":
            result.append(stack.pop())
        if stack:
            stack.pop()

    elif char in priority:

        if char in ["+", "-"] and (
            i == 0 or expression[i - 1] in ["(", "+", "-", "*", "/"]
        ):
            if char == "-":
                stack.append("@")
        else:

            while (
                stack
                and stack[-1] != "("
                and priority.get(stack[-1], 0) >= priority.get(char, 0)
            ):
                if stack[-1] == "@":
                    result.append("-")
                else:
                    result.append(stack.pop())
                stack.pop() if stack and stack[-1] == "@" else None

            stack.append(char)

    i += 1

while stack:
    if stack[-1] == "@":
        result.append("-")
    else:
        result.append(stack.pop())
    stack.pop() if stack and stack[-1] == "@" else None

print(" ".join(result))

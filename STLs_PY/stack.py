"""
@file stack.py
@brief Python栈(stack)用法示例

栈是一种后进先出(LIFO)的数据结构，Python中可以使用列表(list)或双端队列(deque)实现
特点：
1. 后进先出：最后添加的元素最先被移除
2. 基本操作：压栈(push)、弹栈(pop)、查看栈顶(peek)
3. 动态大小：栈的大小可以动态调整
4. 简单高效：使用列表实现时，尾部操作是O(1)时间复杂度

常用操作时间复杂度（使用列表实现）：
- 压栈(push/append)：O(1)（平摊）
- 弹栈(pop)：O(1)
- 查看栈顶(peek)：O(1)
- 判断空栈：O(1)
"""


def main():
    print("========== Python栈(stack)用法示例 ==========")

    # 1. 使用列表实现栈
    print("\n1. 使用列表实现栈:")

    # 创建空栈
    stack1 = []
    print(f"空栈: {stack1}, 大小: {len(stack1)}")

    # 压栈操作
    stack1.append(10)
    stack1.append(20)
    stack1.append(30)
    print(f"压栈后栈: {stack1}, 大小: {len(stack1)}")

    # 查看栈顶（不弹出）
    if stack1:
        top = stack1[-1]
        print(f"栈顶元素: {top}")

    # 弹栈操作
    popped = stack1.pop()
    print(f"弹栈后栈: {stack1}, 弹出的元素: {popped}")

    popped = stack1.pop()
    print(f"再次弹栈后栈: {stack1}, 弹出的元素: {popped}")

    # 判断栈是否为空
    print(f"栈是否为空: {len(stack1) == 0}")
    print(f"栈是否为空(使用not): {not stack1}")

    # 2. 栈的完整实现（类封装）
    print("\n2. 栈的完整实现（类封装）:")

    class Stack:
        def __init__(self):
            self._items = []

        def push(self, item):
            """压栈"""
            self._items.append(item)

        def pop(self):
            """弹栈"""
            if not self.is_empty():
                return self._items.pop()
            raise IndexError("弹栈错误：栈为空")

        def peek(self):
            """查看栈顶元素"""
            if not self.is_empty():
                return self._items[-1]
            raise IndexError("查看栈顶错误：栈为空")

        def is_empty(self):
            """判断栈是否为空"""
            return len(self._items) == 0

        def size(self):
            """返回栈的大小"""
            return len(self._items)

        def clear(self):
            """清空栈"""
            self._items.clear()

        def __str__(self):
            return str(self._items)

    # 使用Stack类
    stack2 = Stack()
    stack2.push("A")
    stack2.push("B")
    stack2.push("C")
    print(f"压栈后栈: {stack2}")
    print(f"栈大小: {stack2.size()}")
    print(f"栈顶元素: {stack2.peek()}")

    popped = stack2.pop()
    print(f"弹栈后栈: {stack2}, 弹出的元素: {popped}")
    print(f"栈是否为空: {stack2.is_empty()}")

    # 3. 使用collections.deque实现栈
    print("\n3. 使用collections.deque实现栈:")

    from collections import deque

    class DequeStack:
        def __init__(self):
            self._items = deque()

        def push(self, item):
            """压栈"""
            self._items.append(item)

        def pop(self):
            """弹栈"""
            if not self.is_empty():
                return self._items.pop()
            raise IndexError("弹栈错误：栈为空")

        def peek(self):
            """查看栈顶元素"""
            if not self.is_empty():
                return self._items[-1]
            raise IndexError("查看栈顶错误：栈为空")

        def is_empty(self):
            """判断栈是否为空"""
            return len(self._items) == 0

        def size(self):
            """返回栈的大小"""
            return len(self._items)

        def clear(self):
            """清空栈"""
            self._items.clear()

        def __str__(self):
            return str(list(self._items))

    # 使用DequeStack类
    stack3 = DequeStack()
    stack3.push(100)
    stack3.push(200)
    stack3.push(300)
    print(f"压栈后栈: {stack3}")
    print(f"栈大小: {stack3.size()}")
    print(f"栈顶元素: {stack3.peek()}")

    # 4. 栈的实际应用场景
    print("\n4. 栈的实际应用场景:")

    # 场景1：括号匹配
    print("场景1: 括号匹配")

    def is_balanced(expression):
        """检查括号是否匹配"""
        stack = []
        matching = {")": "(", "]": "[", "}": "{"}

        for char in expression:
            if char in "([{":
                stack.append(char)
            elif char in ")]}":
                if not stack:
                    return False
                if stack.pop() != matching[char]:
                    return False

        return len(stack) == 0

    test_expressions = ["((()))", "{[()]}", "({[)]}", "((())", "())("]

    for expr in test_expressions:
        print(f"表达式 '{expr}' 括号匹配: {is_balanced(expr)}")

    # 场景2：表达式求值（后缀表达式）
    print("\n场景2: 后缀表达式求值")

    def evaluate_postfix(expression):
        """求值后缀表达式"""
        stack = []
        operators = {
            "+": lambda x, y: x + y,
            "-": lambda x, y: x - y,
            "*": lambda x, y: x * y,
            "/": lambda x, y: x / y,
        }

        for token in expression.split():
            if token.isdigit() or (token[0] == "-" and token[1:].isdigit()):
                stack.append(int(token))
            elif token in operators:
                if len(stack) < 2:
                    raise ValueError("无效的后缀表达式")
                y = stack.pop()
                x = stack.pop()
                result = operators[token](x, y)
                stack.append(result)
            else:
                raise ValueError(f"无效的符号: {token}")

        if len(stack) != 1:
            raise ValueError("无效的后缀表达式")

        return stack[0]

    postfix_expr = "3 4 + 2 * 7 /"
    print(f"后缀表达式: {postfix_expr}")
    print(f"求值结果: {evaluate_postfix(postfix_expr)}")

    # 场景3：浏览器历史记录
    print("\n场景3: 浏览器历史记录")

    class BrowserHistory:
        def __init__(self):
            self.back_stack = []  # 后退栈
            self.forward_stack = []  # 前进栈
            self.current = None

        def visit(self, url):
            """访问新页面"""
            if self.current:
                self.back_stack.append(self.current)
            self.current = url
            self.forward_stack.clear()  # 访问新页面时清空前进栈
            print(f"访问: {url}")

        def back(self):
            """后退"""
            if self.back_stack:
                self.forward_stack.append(self.current)
                self.current = self.back_stack.pop()
                print(f"后退到: {self.current}")
                return self.current
            print("无法后退：已在第一页")
            return None

        def forward(self):
            """前进"""
            if self.forward_stack:
                self.back_stack.append(self.current)
                self.current = self.forward_stack.pop()
                print(f"前进到: {self.current}")
                return self.current
            print("无法前进：已在最后一页")
            return None

        def show_history(self):
            """显示历史记录"""
            print(f"后退栈: {self.back_stack}")
            print(f"当前页面: {self.current}")
            print(f"前进栈: {self.forward_stack}")

    browser = BrowserHistory()
    browser.visit("首页")
    browser.visit("产品页")
    browser.visit("详情页")
    browser.back()
    browser.back()
    browser.forward()
    browser.visit("关于页")  # 访问新页面会清空前进栈
    browser.show_history()

    # 场景4：函数调用栈模拟
    print("\n场景4: 函数调用栈模拟")

    def function_a():
        print("  进入函数A")
        function_b()
        print("  离开函数A")

    def function_b():
        print("  进入函数B")
        function_c()
        print("  离开函数B")

    def function_c():
        print("  进入函数C")
        print("  执行函数C的操作")
        print("  离开函数C")

    print("函数调用栈模拟:")
    function_a()

    # 场景5：深度优先搜索(DFS)
    print("\n场景5: 深度优先搜索(DFS)")

    def dfs(graph, start):
        """使用栈实现深度优先搜索"""
        visited = set()
        stack = [start]

        print(f"从节点{start}开始DFS:")

        while stack:
            vertex = stack.pop()
            if vertex not in visited:
                print(f"  访问节点: {vertex}")
                visited.add(vertex)
                # 将未访问的邻居压栈
                for neighbor in graph.get(vertex, []):
                    if neighbor not in visited:
                        stack.append(neighbor)

        return visited

    # 示例图
    graph = {
        "A": ["B", "C"],
        "B": ["A", "D", "E"],
        "C": ["A", "F"],
        "D": ["B"],
        "E": ["B", "F"],
        "F": ["C", "E"],
    }

    dfs(graph, "A")

    # 5. 栈与递归的关系
    print("\n5. 栈与递归的关系:")

    # 递归实现阶乘
    def factorial_recursive(n):
        """递归实现阶乘"""
        if n <= 1:
            return 1
        return n * factorial_recursive(n - 1)

    # 使用栈模拟递归
    def factorial_stack(n):
        """使用栈模拟递归实现阶乘"""
        stack = []
        result = 1

        # 将递归调用压栈
        while n > 1:
            stack.append(n)
            n -= 1

        # 弹栈并计算
        while stack:
            result *= stack.pop()

        return result

    n = 5
    print(f"计算 {n} 的阶乘:")
    print(f"  递归实现: {factorial_recursive(n)}")
    print(f"  栈模拟实现: {factorial_stack(n)}")

    # 6. 性能提示
    print("\n6. 性能提示:")
    print("1. 使用列表实现栈时，append()和pop()是O(1)操作")
    print("2. 使用deque实现栈在多线程环境中更安全")
    print("3. 栈的深度受限于递归深度限制（默认约1000层）")
    print("4. 对于深度递归问题，考虑使用显式栈避免递归深度限制")
    print("5. 栈操作不会导致内存碎片化")
    print("6. 栈是后进先出结构，适合需要反向处理数据的场景")

    # 7. 常见错误
    print("\n7. 常见错误:")

    # 错误1：空栈弹栈
    print("错误1: 空栈弹栈")
    empty_stack = []
    try:
        empty_stack.pop()
    except IndexError as e:
        print(f"  错误: {e}")

    # 错误2：使用错误的方法
    print("\n错误2: 使用错误的方法")
    stack_wrong = []
    stack_wrong.append(1)
    stack_wrong.append(2)
    # 错误：使用pop(0)而不是pop()，这变成了队列操作
    print(f"  错误使用pop(0): {stack_wrong.pop(0)}，栈变为: {stack_wrong}")

    # 错误3：栈溢出（递归深度）
    print("\n错误3: 栈溢出（递归深度）")

    def recursive_overflow(n):
        if n <= 0:
            return 0
        return 1 + recursive_overflow(n - 1)

    try:
        # 这个调用会导致递归深度错误
        # recursive_overflow(10000)
        print("  递归深度测试已跳过（避免崩溃）")
    except RecursionError as e:
        print(f"  错误: {e}")

    print("\n========== Python栈示例结束 ==========")


if __name__ == "__main__":
    main()

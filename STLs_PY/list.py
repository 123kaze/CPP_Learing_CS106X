"""
@file list.py
@brief Python列表(list)用法示例

list是Python中的动态数组容器，类似于C++中的vector
特点：
1. 动态扩容：自动管理内存，可动态调整大小
2. 随机访问：支持O(1)时间的随机访问
3. 连续存储：元素在内存中连续存储（CPython实现）
4. 尾部操作高效：在尾部插入/删除元素为O(1)时间复杂度（平摊）
5. 支持多种数据类型：可以存储不同类型的元素

常用操作时间复杂度：
- 访问元素：O(1)
- 尾部插入/删除：O(1)（平摊）
- 中间插入/删除：O(n)
- 查找：O(n)
- 切片：O(k)（k为切片大小）
"""


def main():
    print("========== Python列表(list)用法示例 ==========")

    # 1. 创建和初始化列表
    print("\n1. 创建和初始化列表:")

    # 空列表
    lst1 = []
    print(f"空列表: {lst1}, 大小: {len(lst1)}")

    # 使用list()构造函数
    lst2 = list()
    print(f"使用list()创建: {lst2}")

    # 指定大小和初始值（使用列表推导式）
    lst3 = [10] * 5  # 5个元素，每个都是10
    print(f"重复元素列表: {lst3}")

    # 使用初始化列表
    lst4 = [1, 2, 3, 4, 5]
    print(f"初始化列表: {lst4}")

    # 从range创建
    lst5 = list(range(5))
    print(f"从range创建: {lst5}")

    # 从字符串创建
    lst6 = list("hello")
    print(f"从字符串创建: {lst6}")

    # 从元组创建
    lst7 = list((1, 2, 3))
    print(f"从元组创建: {lst7}")

    # 2. 基本操作
    print("\n2. 基本操作:")

    # 添加元素
    lst1.append(100)  # 尾部添加
    lst1.append(200)
    lst1.append(300)
    print(f"append后列表: {lst1}")

    # 扩展列表
    lst1.extend([400, 500])
    print(f"extend后列表: {lst1}")

    # 插入元素
    lst1.insert(1, 150)  # 在位置1插入150
    print(f"insert后列表: {lst1}")

    # 访问元素
    print(f"lst4[2] = {lst4[2]}")  # 随机访问
    print(f"lst4[-1] = {lst4[-1]}")  # 倒数第一个元素
    print(f"lst4[-2] = {lst4[-2]}")  # 倒数第二个元素

    # 3. 切片操作（Python特有）
    print("\n3. 切片操作:")

    lst8 = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    print(f"原始列表: {lst8}")
    print(f"lst8[2:5] = {lst8[2:5]}")  # 索引2到4（不包含5）
    print(f"lst8[:5] = {lst8[:5]}")  # 从开始到索引4
    print(f"lst8[5:] = {lst8[5:]}")  # 从索引5到结束
    print(f"lst8[::2] = {lst8[::2]}")  # 步长为2
    print(f"lst8[::-1] = {lst8[::-1]}")  # 反转列表

    # 4. 修改操作
    print("\n4. 修改操作:")

    # 修改元素
    lst4[2] = 99
    print(f"修改后lst4: {lst4}")

    # 删除元素
    del lst4[2]  # 删除位置2的元素
    print(f"del删除后lst4: {lst4}")

    lst4.remove(4)  # 删除值为4的元素
    print(f"remove删除后lst4: {lst4}")

    popped = lst4.pop()  # 删除并返回最后一个元素
    print(f"pop删除后lst4: {lst4}, 弹出的元素: {popped}")

    popped = lst4.pop(0)  # 删除并返回第一个元素
    print(f"pop(0)删除后lst4: {lst4}, 弹出的元素: {popped}")

    # 清空列表
    lst9 = [1, 2, 3, 4, 5]
    lst9.clear()
    print(f"清空后lst9: {lst9}, 大小: {len(lst9)}")

    # 5. 查找和统计
    print("\n5. 查找和统计:")

    lst10 = [5, 3, 8, 1, 9, 2, 5, 3, 5]

    # 查找元素索引
    index = lst10.index(8)
    print(f"元素8的索引: {index}")

    # 统计元素出现次数
    count_5 = lst10.count(5)
    print(f"元素5出现的次数: {count_5}")

    # 检查元素是否存在
    print(f"9是否在列表中: {9 in lst10}")
    print(f"10是否在列表中: {10 in lst10}")

    # 6. 排序和反转
    print("\n6. 排序和反转:")

    # 排序（原地）
    lst11 = [5, 3, 8, 1, 9, 2]
    lst11.sort()
    print(f"排序后lst11: {lst11}")

    # 降序排序
    lst11.sort(reverse=True)
    print(f"降序排序后lst11: {lst11}")

    # 使用sorted()函数（返回新列表）
    lst12 = [5, 3, 8, 1, 9, 2]
    sorted_lst = sorted(lst12)
    print(f"原列表: {lst12}")
    print(f"sorted()返回的新列表: {sorted_lst}")

    # 反转
    lst13 = [1, 2, 3, 4, 5]
    lst13.reverse()
    print(f"反转后lst13: {lst13}")

    # 7. 列表推导式（Python特有）
    print("\n7. 列表推导式:")

    # 创建平方列表
    squares = [x**2 for x in range(10)]
    print(f"平方列表: {squares}")

    # 创建偶数平方列表
    even_squares = [x**2 for x in range(10) if x % 2 == 0]
    print(f"偶数平方列表: {even_squares}")

    # 嵌套列表推导式
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    flattened = [num for row in matrix for num in row]
    print(f"矩阵: {matrix}")
    print(f"展平后: {flattened}")

    # 8. 多维列表
    print("\n8. 多维列表:")

    # 二维列表
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

    print("二维列表矩阵:")
    for row in matrix:
        print(f"  {row}")

    # 访问二维列表元素
    print(f"matrix[1][2] = {matrix[1][2]}")

    # 使用列表推导式创建二维列表
    matrix2 = [[i * 3 + j + 1 for j in range(3)] for i in range(3)]
    print("使用列表推导式创建的矩阵:")
    for row in matrix2:
        print(f"  {row}")

    # 9. 列表复制
    print("\n9. 列表复制:")

    # 浅复制（引用复制）
    original = [[1, 2], [3, 4]]
    shallow_copy = original.copy()
    original[0][0] = 99
    print(f"原列表: {original}")
    print(f"浅复制列表: {shallow_copy}")
    print("注意：浅复制只复制了外层列表，内层列表仍然是引用")

    # 深复制
    import copy

    original2 = [[1, 2], [3, 4]]
    deep_copy = copy.deepcopy(original2)
    original2[0][0] = 99
    print(f"原列表: {original2}")
    print(f"深复制列表: {deep_copy}")

    # 10. 列表性能提示
    print("\n10. 性能提示:")
    print("1. 如果需要频繁在尾部添加元素，列表是最佳选择")
    print("2. 如果需要频繁在中间插入/删除，考虑使用collections.deque")
    print("3. 列表推导式比循环+append更高效")
    print("4. 使用in操作符检查元素是否存在是O(n)操作")
    print("5. 切片操作会创建新列表，注意内存使用")
    print("6. 对于大量数值计算，考虑使用NumPy数组")

    # 11. 实际应用场景
    print("\n11. 实际应用场景:")

    # 场景1：栈实现
    print("场景1: 栈实现")
    stack = []
    stack.append(1)  # push
    stack.append(2)
    stack.append(3)
    print(f"栈: {stack}")
    top = stack.pop()  # pop
    print(f"弹出: {top}, 栈: {stack}")

    # 场景2：队列实现（使用collections.deque更高效）
    print("\n场景2: 队列实现")
    from collections import deque

    queue = deque()
    queue.append(1)  # enqueue
    queue.append(2)
    queue.append(3)
    print(f"队列: {queue}")
    front = queue.popleft()  # dequeue
    print(f"出队: {front}, 队列: {queue}")

    # 场景3：列表作为缓冲区
    print("\n场景3: 列表作为缓冲区")
    buffer = []
    for i in range(5):
        buffer.append(f"数据{i}")
        if len(buffer) > 3:
            buffer.pop(0)  # 移除最旧的数据
        print(f"缓冲区: {buffer}")

    print("\n========== Python列表示例结束 ==========")


if __name__ == "__main__":
    main()

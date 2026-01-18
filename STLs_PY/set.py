"""
@file set.py
@brief Python集合(set)用法示例

set是Python中的无序不重复元素集，类似于C++中的set/unordered_set
特点：
1. 无序性：元素没有固定顺序
2. 唯一性：集合中不允许重复元素
3. 哈希表实现：内部使用哈希表实现，保证O(1)平均时间复杂度
4. 数学运算：支持交集、并集、差集等数学运算
5. 可变性：set是可变的，frozenset是不可变的

常用操作时间复杂度（平均情况）：
- 添加元素：O(1)
- 删除元素：O(1)
- 查找元素：O(1)
- 集合运算：O(len(s) + len(t))

最坏情况时间复杂度：O(n)（哈希冲突时）
"""


def main():
    print("========== Python集合(set)用法示例 ==========")

    # 1. 创建和初始化集合
    print("\n1. 创建和初始化集合:")

    # 空集合（必须使用set()，不能使用{}，因为{}创建的是字典）
    s1 = set()
    print(f"空集合: {s1}, 大小: {len(s1)}")

    # 使用初始化列表
    s2 = {1, 2, 3, 4, 5}
    print(f"初始化集合: {s2}")

    # 从列表创建（自动去重）
    s3 = set([1, 2, 2, 3, 3, 3, 4, 5])
    print(f"从列表创建（自动去重）: {s3}")

    # 从字符串创建
    s4 = set("hello")
    print(f"从字符串创建: {s4}")

    # 使用集合推导式
    s5 = {x**2 for x in range(5)}
    print(f"集合推导式创建: {s5}")

    # 不可变集合（frozenset）
    fs = frozenset([1, 2, 3, 4, 5])
    print(f"不可变集合: {fs}")

    # 2. 基本操作
    print("\n2. 基本操作:")

    # 添加元素
    s1.add(10)
    s1.add(20)
    s1.add(30)
    print(f"添加元素后s1: {s1}")

    # 添加重复元素（不会有效果）
    s1.add(10)
    print(f"添加重复元素10后s1: {s1}")

    # 删除元素
    s1.remove(20)  # 如果元素不存在会抛出KeyError
    print(f"remove(20)后s1: {s1}")

    s1.discard(30)  # 如果元素不存在不会抛出异常
    print(f"discard(30)后s1: {s1}")

    s1.discard(100)  # 元素100不存在，不会抛出异常
    print(f"discard(100)后s1: {s1}")

    # 随机删除并返回一个元素
    s6 = {1, 2, 3, 4, 5}
    popped = s6.pop()
    print(f"pop()后s6: {s6}, 弹出的元素: {popped}")

    # 清空集合
    s7 = {1, 2, 3, 4, 5}
    s7.clear()
    print(f"清空后s7: {s7}, 大小: {len(s7)}")

    # 3. 集合运算
    print("\n3. 集合运算:")

    A = {1, 2, 3, 4, 5}
    B = {4, 5, 6, 7, 8}

    print(f"集合A: {A}")
    print(f"集合B: {B}")

    # 并集
    union = A | B
    print(f"并集 A | B: {union}")
    print(f"并集 A.union(B): {A.union(B)}")

    # 交集
    intersection = A & B
    print(f"交集 A & B: {intersection}")
    print(f"交集 A.intersection(B): {A.intersection(B)}")

    # 差集
    difference = A - B
    print(f"差集 A - B: {difference}")
    print(f"差集 A.difference(B): {A.difference(B)}")

    # 对称差集（在A或B中，但不同时在两者中）
    symmetric_diff = A ^ B
    print(f"对称差集 A ^ B: {symmetric_diff}")
    print(f"对称差集 A.symmetric_difference(B): {A.symmetric_difference(B)}")

    # 4. 集合关系测试
    print("\n4. 集合关系测试:")

    X = {1, 2, 3}
    Y = {1, 2, 3, 4, 5}
    Z = {4, 5, 6}

    print(f"集合X: {X}")
    print(f"集合Y: {Y}")
    print(f"集合Z: {Z}")

    # 子集测试
    print(f"X ⊆ Y (X是Y的子集): {X.issubset(Y)}")
    print(f"X <= Y: {X <= Y}")
    print(f"X < Y (X是Y的真子集): {X < Y}")

    # 超集测试
    print(f"Y ⊇ X (Y是X的超集): {Y.issuperset(X)}")
    print(f"Y >= X: {Y >= X}")
    print(f"Y > X (Y是X的真超集): {Y > X}")

    # 不相交测试
    print(f"X和Z不相交: {X.isdisjoint(Z)}")
    print(f"Y和Z不相交: {Y.isdisjoint(Z)}")

    # 5. 更新操作
    print("\n5. 更新操作:")

    S = {1, 2, 3}
    T = {3, 4, 5}
    U = {5, 6, 7}

    print(f"原始集合S: {S}")
    print(f"集合T: {T}")
    print(f"集合U: {U}")

    # 更新为并集
    S.update(T)
    print(f"S.update(T)后S: {S}")

    # 更新为交集
    S = {1, 2, 3}
    S.intersection_update(T)
    print(f"S.intersection_update(T)后S: {S}")

    # 更新为差集
    S = {1, 2, 3, 4}
    S.difference_update({2, 3})
    print(f"S.difference_update({{2, 3}})后S: {S}")

    # 更新为对称差集
    S = {1, 2, 3}
    S.symmetric_difference_update({3, 4, 5})
    print(f"S.symmetric_difference_update({{3, 4, 5}})后S: {S}")

    # 6. 集合推导式
    print("\n6. 集合推导式:")

    # 创建平方集合
    squares = {x**2 for x in range(10)}
    print(f"平方集合: {squares}")

    # 过滤集合
    numbers = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
    even_squares = {x**2 for x in numbers if x % 2 == 0}
    print(f"原始集合: {numbers}")
    print(f"偶数平方集合: {even_squares}")

    # 7. 实际应用场景
    print("\n7. 实际应用场景:")

    # 场景1：去重
    print("场景1: 列表去重")
    data = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5]
    unique_data = list(set(data))
    print(f"原始数据: {data}")
    print(f"去重后: {unique_data}")

    # 场景2：查找共同元素
    print("\n场景2: 查找共同元素")
    students_math = {"Alice", "Bob", "Charlie", "David"}
    students_physics = {"Bob", "David", "Eve", "Frank"}
    common = students_math & students_physics
    print(f"数学课学生: {students_math}")
    print(f"物理课学生: {students_physics}")
    print(f"两门课都上的学生: {common}")

    # 场景3：权限管理
    print("\n场景3: 权限管理")

    # 用户权限
    user_permissions = {
        "admin": {"read", "write", "delete", "manage_users"},
        "editor": {"read", "write"},
        "viewer": {"read"},
    }

    # 检查权限
    user_role = "editor"
    required_permission = "write"

    if required_permission in user_permissions[user_role]:
        print(f"用户'{user_role}'有'{required_permission}'权限")
    else:
        print(f"用户'{user_role}'没有'{required_permission}'权限")

    # 场景4：数据验证
    print("\n场景4: 数据验证")

    valid_colors = {"red", "green", "blue", "yellow", "black", "white"}
    user_input = "red"

    if user_input in valid_colors:
        print(f"颜色'{user_input}'是有效的")
    else:
        print(f"颜色'{user_input}'无效，有效颜色: {valid_colors}")

    # 8. 性能提示
    print("\n8. 性能提示:")
    print("1. 集合基于哈希表实现，平均O(1)时间复杂度")
    print("2. 集合元素必须是不可变类型（字符串、数字、元组等）")
    print("3. 使用in操作符检查元素是否存在是O(1)操作")
    print("4. 集合推导式比循环更高效")
    print("5. 对于大量数据的去重，集合比列表更高效")
    print("6. 集合运算（交集、并集等）比手动循环更高效")
    print("7. 如果需要不可变集合，使用frozenset")
    print("8. 集合不保持元素插入顺序（Python 3.7+中字典保持顺序，但集合不保证）")

    # 9. 与列表的性能比较
    print("\n9. 与列表的性能比较:")

    import time

    # 测试查找性能
    test_size = 10000
    test_list = list(range(test_size))
    test_set = set(range(test_size))

    # 测试列表查找
    start = time.time()
    for i in range(test_size):
        if i in test_list:
            pass
    list_time = time.time() - start

    # 测试集合查找
    start = time.time()
    for i in range(test_size):
        if i in test_set:
            pass
    set_time = time.time() - start

    print(f"查找{test_size}个元素:")
    print(f"  列表: {list_time:.4f}秒")
    print(f"  集合: {set_time:.4f}秒")
    print(f"  集合比列表快{list_time/set_time:.1f}倍")

    print("\n========== Python集合示例结束 ==========")


if __name__ == "__main__":
    main()

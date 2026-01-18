"""
@file tuple.py
@brief Python元组(tuple)用法示例

元组是Python中的不可变序列，类似于C++中的tuple或数组
特点：
1. 不可变性：创建后不能修改元素（但可以包含可变对象）
2. 有序性：元素保持插入顺序
3. 可哈希性：如果所有元素都是可哈希的，元组本身也是可哈希的
4. 内存高效：比列表更节省内存
5. 解包操作：支持多种解包方式

常用操作时间复杂度：
- 访问元素：O(1)
- 查找元素：O(n)
- 切片操作：O(k)（k为切片大小）
- 成员测试：O(n)
"""


def main():
    print("========== Python元组(tuple)用法示例 ==========")

    # 1. 创建和初始化元组
    print("\n1. 创建和初始化元组:")

    # 空元组
    t1 = ()
    print(f"空元组: {t1}, 大小: {len(t1)}")

    # 单个元素的元组（注意逗号）
    t2 = (42,)  # 必须有逗号
    t2_wrong = 42  # 这不是元组，是整数
    print(f"单个元素元组: {t2}, 类型: {type(t2)}")
    print(f"没有逗号: {t2_wrong}, 类型: {type(t2_wrong)}")

    # 多个元素的元组
    t3 = (1, 2, 3, 4, 5)
    print(f"多个元素元组: {t3}")

    # 不使用括号创建
    t4 = 1, 2, 3
    print(f"不使用括号: {t4}, 类型: {type(t4)}")

    # 使用tuple()构造函数
    t5 = tuple([1, 2, 3])
    print(f"从列表创建: {t5}")

    t6 = tuple("hello")
    print(f"从字符串创建: {t6}")

    # 2. 基本操作
    print("\n2. 基本操作:")

    # 访问元素
    print(f"t3[0] = {t3[0]}")
    print(f"t3[-1] = {t3[-1]}")  # 最后一个元素
    print(f"t3[1:3] = {t3[1:3]}")  # 切片

    # 元组是不可变的，尝试修改会报错
    try:
        t3[0] = 99
    except TypeError as e:
        print(f"尝试修改元组错误: {e}")

    # 但可以重新赋值
    t3 = (10, 20, 30)
    print(f"重新赋值后t3: {t3}")

    # 3. 元组解包
    print("\n3. 元组解包:")

    # 基本解包
    point = (10, 20)
    x, y = point
    print(f"点: {point}, 解包后: x={x}, y={y}")

    # 交换变量
    a, b = 1, 2
    print(f"交换前: a={a}, b={b}")
    a, b = b, a  # 使用元组解包交换
    print(f"交换后: a={a}, b={b}")

    # 扩展解包（Python 3+）
    numbers = (1, 2, 3, 4, 5)
    first, *middle, last = numbers
    print(f"元组: {numbers}")
    print(f"解包: first={first}, middle={middle}, last={last}")

    # 忽略某些元素
    _, height, _ = (100, 175, 80)  # 只关心身高
    print(f"身高: {height}cm")

    # 4. 元组运算
    print("\n4. 元组运算:")

    # 连接元组
    t7 = (1, 2, 3)
    t8 = (4, 5, 6)
    t9 = t7 + t8
    print(f"连接: {t7} + {t8} = {t9}")

    # 重复元组
    t10 = t7 * 3
    print(f"重复: {t7} * 3 = {t10}")

    # 成员测试
    print(f"3在t7中: {3 in t7}")
    print(f"9在t7中: {9 in t7}")

    # 5. 元组方法
    print("\n5. 元组方法:")

    t11 = (1, 2, 3, 2, 4, 2, 5)

    # 计数元素
    count_2 = t11.count(2)
    print(f"t11中2出现的次数: {count_2}")

    # 查找元素索引
    index_3 = t11.index(3)
    print(f"元素3的索引: {index_3}")

    # 查找下一个出现的索引
    index_2_after_2 = t11.index(2, 2)  # 从索引2开始查找
    print(f"从索引2开始查找2: {index_2_after_2}")

    # 6. 嵌套元组
    print("\n6. 嵌套元组:")

    # 二维元组
    matrix = ((1, 2, 3), (4, 5, 6), (7, 8, 9))

    print("二维元组矩阵:")
    for row in matrix:
        print(f"  {row}")

    # 访问嵌套元素
    print(f"matrix[1][2] = {matrix[1][2]}")

    # 包含可变对象的元组
    mutable_tuple = ([1, 2], [3, 4])
    print(f"包含列表的元组: {mutable_tuple}")

    # 可以修改元组中的列表
    mutable_tuple[0].append(3)
    print(f"修改后: {mutable_tuple}")
    print("注意：元组本身不可变，但可以修改其中的可变对象")

    # 7. 命名元组
    print("\n7. 命名元组:")

    from collections import namedtuple

    # 定义命名元组类型
    Point = namedtuple("Point", ["x", "y"])
    Color = namedtuple("Color", ["red", "green", "blue"])

    # 创建命名元组实例
    p1 = Point(10, 20)
    p2 = Point(x=30, y=40)
    red = Color(255, 0, 0)

    print(f"点1: {p1}, x={p1.x}, y={p1.y}")
    print(f"点2: {p2}, x={p2[0]}, y={p2[1]}")  # 也可以像普通元组一样访问

    # 命名元组的方法
    print(f"点1的字段: {p1._fields}")
    p1_dict = p1._asdict()
    print(f"点1转为字典: {p1_dict}")

    # 替换字段值
    p3 = p1._replace(x=99)
    print(f"替换后点3: {p3}")

    # 8. 元组与字典
    print("\n8. 元组与字典:")

    # 元组作为字典的键
    location_map = {
        (40.7128, -74.0060): "纽约",
        (51.5074, -0.1278): "伦敦",
        (35.6762, 139.6503): "东京",
    }

    print("坐标字典:")
    for coords, city in location_map.items():
        print(f"  {coords}: {city}")

    # 查找坐标对应的城市
    ny_coords = (40.7128, -74.0060)
    print(f"坐标{ny_coords}对应的城市: {location_map.get(ny_coords)}")

    # 字典的items()返回键值对元组
    person = {"name": "Alice", "age": 25, "city": "北京"}
    print("\n字典items()返回的元组:")
    for key, value in person.items():
        print(f"  {key}: {value}")

    # 9. 实际应用场景
    print("\n9. 实际应用场景:")

    # 场景1：函数返回多个值
    print("场景1: 函数返回多个值")

    def get_statistics(numbers):
        """返回统计信息"""
        if not numbers:
            return (0, 0, 0.0)  # 返回默认值而不是None
        return min(numbers), max(numbers), sum(numbers) / len(numbers)

    data = [10, 20, 30, 40, 50]
    min_val, max_val, avg_val = get_statistics(data)
    print(f"数据: {data}")
    print(f"最小值: {min_val}, 最大值: {max_val}, 平均值: {avg_val:.2f}")

    # 测试空列表情况
    empty_data = []
    min_val2, max_val2, avg_val2 = get_statistics(empty_data)
    print(f"空数据: {empty_data}")
    print(f"空数据统计: 最小值={min_val2}, 最大值={max_val2}, 平均值={avg_val2:.2f}")

    # 场景2：坐标系统
    print("\n场景2: 坐标系统")

    def distance(p1, p2):
        """计算两点间距离"""
        x1, y1 = p1
        x2, y2 = p2
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    point_a = (0, 0)
    point_b = (3, 4)
    dist = distance(point_a, point_b)
    print(f"点A{point_a}到点B{point_b}的距离: {dist}")

    # 场景3：RGB颜色
    print("\n场景3: RGB颜色")

    def rgb_to_hex(rgb):
        """RGB元组转十六进制"""
        r, g, b = rgb
        return f"#{r:02x}{g:02x}{b:02x}"

    colors = {
        "红色": (255, 0, 0),
        "绿色": (0, 255, 0),
        "蓝色": (0, 0, 255),
        "白色": (255, 255, 255),
        "黑色": (0, 0, 0),
    }

    print("颜色RGB值和十六进制:")
    for name, rgb in colors.items():
        hex_code = rgb_to_hex(rgb)
        print(f"  {name}: RGB{rgb} -> {hex_code}")

    # 场景4：数据库记录
    print("\n场景4: 数据库记录（简化）")

    # 模拟数据库查询结果
    users = [
        (1, "Alice", "alice@example.com", 25),
        (2, "Bob", "bob@example.com", 30),
        (3, "Charlie", "charlie@example.com", 35),
    ]

    print("用户数据:")
    for user in users:
        id, name, email, age = user
        print(f"  ID: {id}, 姓名: {name}, 邮箱: {email}, 年龄: {age}")

    # 10. 性能提示
    print("\n10. 性能提示:")
    print("1. 元组比列表更节省内存，创建速度更快")
    print("2. 元组不可变，可以作为字典的键")
    print("3. 元组在函数参数和返回值中很有用")
    print("4. 对于不会修改的数据，使用元组而不是列表")
    print("5. 命名元组可以提高代码可读性")
    print("6. 元组解包是Pythonic的写法")
    print("7. 元组的哈希性使其适合用于集合和字典键")

    # 11. 元组与列表的比较
    print("\n11. 元组与列表的比较:")

    import sys
    import time

    # 内存比较
    list_obj = [1, 2, 3, 4, 5]
    tuple_obj = (1, 2, 3, 4, 5)

    list_size = sys.getsizeof(list_obj)
    tuple_size = sys.getsizeof(tuple_obj)

    print(f"相同元素的内存占用:")
    print(f"  列表: {list_size} 字节")
    print(f"  元组: {tuple_size} 字节")
    print(f"  元组比列表节省 {list_size - tuple_size} 字节")

    # 创建速度比较
    start = time.time()
    for _ in range(1000000):
        _ = [1, 2, 3, 4, 5]
    list_time = time.time() - start

    start = time.time()
    for _ in range(1000000):
        _ = (1, 2, 3, 4, 5)
    tuple_time = time.time() - start

    print(f"\n创建速度比较（100万次）:")
    print(f"  列表: {list_time:.4f}秒")
    print(f"  元组: {tuple_time:.4f}秒")
    print(f"  元组比列表快 {list_time/tuple_time:.1f}倍")

    print("\n========== Python元组示例结束 ==========")


if __name__ == "__main__":
    main()

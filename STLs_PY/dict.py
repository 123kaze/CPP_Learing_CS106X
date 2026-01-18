"""
@file dict.py
@brief Python字典(dict)用法示例

dict是Python中的关联容器，存储键值对，类似于C++中的map/unordered_map
特点：
1. 键值对存储：每个元素是一个key-value对
2. 键唯一性：每个键在字典中只能出现一次
3. 无序性：Python 3.7+中字典保持插入顺序，但本质上是无序容器
4. 哈希表实现：内部使用哈希表实现，保证O(1)平均时间复杂度
5. 快速查找：通过键可以快速查找对应的值

常用操作时间复杂度（平均情况）：
- 插入元素：O(1)
- 删除元素：O(1)
- 查找元素：O(1)
- 访问元素：O(1)

最坏情况时间复杂度：O(n)（哈希冲突时）
"""


def main():
    print("========== Python字典(dict)用法示例 ==========")

    # 1. 创建和初始化字典
    print("\n1. 创建和初始化字典:")

    # 空字典
    d1 = {}
    print(f"空字典: {d1}, 大小: {len(d1)}")

    # 使用dict()构造函数
    d2 = dict()
    print(f"使用dict()创建: {d2}")

    # 使用初始化列表
    d3 = {"Alice": 25, "Bob": 30, "Charlie": 35}
    print(f"初始化字典: {d3}")

    # 从键值对列表创建
    d4 = dict([("David", 40), ("Eve", 28), ("Frank", 32)])
    print(f"从列表创建: {d4}")

    # 使用关键字参数创建
    d5 = dict(John=28, Mary=32, Tom=45)
    print(f"使用关键字参数创建: {d5}")

    # 使用字典推导式
    d6 = {x: x**2 for x in range(5)}
    print(f"字典推导式创建: {d6}")

    # 2. 基本操作
    print("\n2. 基本操作:")

    # 添加/修改元素
    d1["John"] = 28
    d1["Mary"] = 32
    d1["Tom"] = 45
    print(f"添加元素后d1: {d1}")

    # 修改元素
    d1["John"] = 29
    print(f"修改John年龄后d1: {d1}")

    # 访问元素
    print(f"d1['John'] = {d1['John']}")
    print(f"d1.get('Mary') = {d1.get('Mary')}")

    # 访问不存在的键
    print(f"d1.get('Jane') = {d1.get('Jane')}")  # 返回None
    print(f"d1.get('Jane', '未知') = {d1.get('Jane', '未知')}")  # 返回默认值

    # 使用setdefault()：如果键不存在则设置默认值
    age = d1.setdefault("Jane", 30)
    print(f"setdefault后d1: {d1}, Jane的年龄: {age}")

    # 3. 删除操作
    print("\n3. 删除操作:")

    d7 = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
    print(f"原始字典: {d7}")

    # 删除指定键
    del d7["C"]
    print(f"删除键'C'后: {d7}")

    # 使用pop()删除并返回值
    value = d7.pop("B")
    print(f"pop('B')后: {d7}, 弹出的值: {value}")

    # 使用popitem()删除并返回最后一个键值对（Python 3.7+）
    key, value = d7.popitem()
    print(f"popitem()后: {d7}, 弹出的键值对: {key}={value}")

    # 清空字典
    d8 = {"X": 10, "Y": 20, "Z": 30}
    d8.clear()
    print(f"清空后d8: {d8}, 大小: {len(d8)}")

    # 4. 查找和检查
    print("\n4. 查找和检查:")

    # 检查键是否存在
    print(f"'Alice'在d3中: {'Alice' in d3}")
    print(f"'David'在d3中: {'David' in d3}")

    # 检查值是否存在
    print(f"值25在d3中: {25 in d3.values()}")

    # 获取所有键、值、键值对
    print(f"d3的键: {list(d3.keys())}")
    print(f"d3的值: {list(d3.values())}")
    print(f"d3的键值对: {list(d3.items())}")

    # 5. 遍历字典
    print("\n5. 遍历字典:")

    print("遍历键:")
    for key in d3:
        print(f"  {key}")

    print("\n遍历键值对:")
    for key, value in d3.items():
        print(f"  {key}: {value}")

    print("\n遍历值:")
    for value in d3.values():
        print(f"  {value}")

    # 6. 字典推导式（Python特有）
    print("\n6. 字典推导式:")

    # 创建平方字典
    squares = {x: x**2 for x in range(5)}
    print(f"平方字典: {squares}")

    # 过滤字典
    original = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
    filtered = {k: v for k, v in original.items() if v % 2 == 0}
    print(f"原始字典: {original}")
    print(f"过滤后（值为偶数）: {filtered}")

    # 转换键值
    transformed = {k.upper(): v * 10 for k, v in original.items()}
    print(f"转换后（键大写，值×10）: {transformed}")

    # 7. 字典合并和更新
    print("\n7. 字典合并和更新:")

    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 3, "c": 4}
    dict3 = {"d": 5, "e": 6}

    # 使用update()合并
    dict1.update(dict2)
    print(f"update后dict1: {dict1}")  # dict2的b会覆盖dict1的b

    # 使用**操作符合并（Python 3.5+）
    merged = {**dict1, **dict3}
    print(f"合并dict1和dict3: {merged}")

    # 使用|操作符合并（Python 3.9+）
    # merged = dict1 | dict3

    # 8. 嵌套字典
    print("\n8. 嵌套字典:")

    # 二维字典
    students = {
        "Alice": {"age": 25, "grade": "A"},
        "Bob": {"age": 30, "grade": "B"},
        "Charlie": {"age": 35, "grade": "A+"},
    }

    print("学生信息:")
    for name, info in students.items():
        print(f"  {name}: 年龄={info['age']}, 成绩={info['grade']}")

    # 访问嵌套字典
    print(f"Alice的成绩: {students['Alice']['grade']}")

    # 9. 默认字典（collections.defaultdict）
    print("\n9. 默认字典（collections.defaultdict）:")

    from collections import defaultdict

    # 默认值为0的字典
    word_count = defaultdict(int)
    text = "apple banana apple cherry banana apple date"

    for word in text.split():
        word_count[word] += 1

    print(f"文本: {text}")
    print(f"单词统计: {dict(word_count)}")

    # 默认值为列表的字典
    grade_book = defaultdict(list)
    scores = [
        ("Alice", 85),
        ("Bob", 92),
        ("Charlie", 85),
        ("David", 78),
        ("Eve", 92),
        ("Frank", 78),
    ]

    for name, score in scores:
        grade_book[score].append(name)

    print("\n按分数分组的学生:")
    for score, names in sorted(grade_book.items()):
        print(f"  分数{score}: {', '.join(names)}")

    # 10. 有序字典（collections.OrderedDict）
    print("\n10. 有序字典（collections.OrderedDict）:")

    from collections import OrderedDict

    # 创建有序字典
    od = OrderedDict()
    od["first"] = 1
    od["second"] = 2
    od["third"] = 3

    print("有序字典（保持插入顺序）:")
    for key, value in od.items():
        print(f"  {key}: {value}")

    # 移动元素到末尾
    od.move_to_end("first")
    print(f"移动'first'到末尾后: {list(od.items())}")

    # 11. 实际应用场景
    print("\n11. 实际应用场景:")

    # 场景1：缓存实现
    print("场景1: 缓存实现")

    class SimpleCache:
        def __init__(self, max_size=3):
            self.cache = {}
            self.max_size = max_size
            self.access_order = []

        def get(self, key):
            if key in self.cache:
                # 更新访问顺序
                self.access_order.remove(key)
                self.access_order.insert(0, key)
                return self.cache[key]
            return None

        def put(self, key, value):
            if key in self.cache:
                # 更新现有键
                self.cache[key] = value
                self.access_order.remove(key)
                self.access_order.insert(0, key)
            else:
                # 检查缓存是否已满
                if len(self.cache) >= self.max_size:
                    # 移除最久未使用的
                    lru_key = self.access_order.pop()
                    del self.cache[lru_key]
                    print(f"  缓存已满，移除键{lru_key}")

                # 添加新条目
                self.cache[key] = value
                self.access_order.insert(0, key)

            print(f"  当前缓存: {self.cache}")

    cache = SimpleCache(max_size=3)
    cache.put(1, "Data1")
    cache.put(2, "Data2")
    cache.put(3, "Data3")
    cache.get(1)  # 访问键1，应该更新顺序
    cache.put(4, "Data4")  # 应该移除最久未使用的(2)

    # 场景2：配置管理
    print("\n场景2: 配置管理")

    config = {
        "app_name": "MyApp",
        "version": "1.0.0",
        "debug": True,
        "database": {"host": "localhost", "port": 5432, "name": "mydb"},
        "features": ["auth", "logging", "cache"],
    }

    print("应用配置:")
    for key, value in config.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for subkey, subvalue in value.items():
                print(f"    {subkey}: {subvalue}")
        else:
            print(f"  {key}: {value}")

    # 12. 性能提示
    print("\n12. 性能提示:")
    print("1. 字典基于哈希表实现，平均O(1)时间复杂度")
    print("2. 键必须是不可变类型（字符串、数字、元组等）")
    print("3. 使用in操作符检查键是否存在是O(1)操作")
    print("4. 字典推导式比循环更高效")
    print("5. 对于大量数据，考虑字典的内存使用")
    print("6. Python 3.6+中字典保持插入顺序，但不要依赖此特性进行排序")
    print("7. 使用collections.defaultdict可以简化代码")
    print("8. 使用dict.get()避免KeyError异常")

    print("\n========== Python字典示例结束 ==========")


if __name__ == "__main__":
    main()

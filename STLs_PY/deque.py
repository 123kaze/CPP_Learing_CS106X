"""
@file deque.py
@brief Python双端队列(collections.deque)用法示例

deque是Python中的双端队列，类似于C++中的deque
特点：
1. 双端操作：支持从两端高效地添加和删除元素
2. 线程安全：deque是线程安全的
3. 固定长度：可以指定最大长度，当队列满时自动丢弃另一端元素
4. 高效操作：从两端添加/删除元素的时间复杂度为O(1)
5. 内存高效：使用双向链表实现，内存使用比列表更高效

常用操作时间复杂度：
- 两端添加/删除元素：O(1)
- 中间插入/删除元素：O(n)
- 随机访问元素：O(n)
- 旋转操作：O(k)（k为旋转步数）
"""

from collections import deque


def main():
    print("========== Python双端队列(deque)用法示例 ==========")

    # 1. 创建和初始化deque
    print("\n1. 创建和初始化deque:")

    # 空deque
    dq1 = deque()
    print(f"空deque: {dq1}, 大小: {len(dq1)}")

    # 从可迭代对象创建
    dq2 = deque([1, 2, 3, 4, 5])
    print(f"从列表创建: {dq2}")

    # 指定最大长度
    dq3 = deque([1, 2, 3, 4, 5], maxlen=5)
    print(f"指定最大长度5: {dq3}")

    # 从字符串创建
    dq4 = deque("hello")
    print(f"从字符串创建: {dq4}")

    # 2. 基本操作 - 添加元素
    print("\n2. 基本操作 - 添加元素:")

    # 右端添加（类似列表的append）
    dq1.append(10)
    dq1.append(20)
    dq1.append(30)
    print(f"右端添加后dq1: {dq1}")

    # 左端添加
    dq1.appendleft(5)
    dq1.appendleft(0)
    print(f"左端添加后dq1: {dq1}")

    # 右端扩展
    dq1.extend([40, 50])
    print(f"右端扩展后dq1: {dq1}")

    # 左端扩展
    dq1.extendleft([-5, -10])
    print(f"左端扩展后dq1: {dq1}")

    # 3. 基本操作 - 删除元素
    print("\n3. 基本操作 - 删除元素:")

    # 右端删除（类似列表的pop）
    right = dq1.pop()
    print(f"右端删除后dq1: {dq1}, 删除的元素: {right}")

    # 左端删除
    left = dq1.popleft()
    print(f"左端删除后dq1: {dq1}, 删除的元素: {left}")

    # 删除指定元素
    dq5 = deque([1, 2, 3, 2, 4, 2, 5])
    print(f"原始dq5: {dq5}")
    dq5.remove(2)  # 删除第一个出现的2
    print(f"remove(2)后dq5: {dq5}")

    # 清空deque
    dq6 = deque([1, 2, 3, 4, 5])
    dq6.clear()
    print(f"清空后dq6: {dq6}, 大小: {len(dq6)}")

    # 4. 访问元素
    print("\n4. 访问元素:")

    dq7 = deque([10, 20, 30, 40, 50])
    print(f"dq7: {dq7}")

    # 通过索引访问（O(n)操作）
    print(f"dq7[2] = {dq7[2]}")
    print(f"dq7[-1] = {dq7[-1]}")
    dq7.popleft()  # 移除一个元素以演示索引变化

    print(f"移除左端元素后dq7: {dq7}, dq7[2] = {dq7[2]}")

    # 计数元素
    dq8 = deque([1, 2, 3, 2, 4, 2, 5])
    count_2 = dq8.count(2)
    print(f"dq8中2出现的次数: {count_2}")

    # 查找元素索引
    dq9 = deque(["a", "b", "c", "d", "e"])
    try:
        index = dq9.index("c")
        print(f"元素'c'在dq9中的索引: {index}")
    except ValueError:
        print("元素不在deque中")

    # 5. 旋转操作
    print("\n5. 旋转操作:")

    dq10 = deque([1, 2, 3, 4, 5])
    print(f"原始dq10: {dq10}")

    # 正数旋转（向右旋转）
    dq10.rotate(2)
    print(f"rotate(2)后dq10: {dq10}")

    # 负数旋转（向左旋转）
    dq10.rotate(-3)
    print(f"rotate(-3)后dq10: {dq10}")

    # 6. 最大长度特性
    print("\n6. 最大长度特性:")

    # 创建固定长度的deque
    dq11 = deque(maxlen=3)
    dq11.append(1)
    dq11.append(2)
    dq11.append(3)
    print(f"添加3个元素后dq11: {dq11}")

    # 超过最大长度时，另一端元素被丢弃
    dq11.append(4)
    print(f"添加第4个元素后dq11: {dq11}")  # 1被丢弃

    dq11.appendleft(0)
    print(f"左端添加元素后dq11: {dq11}")  # 4被丢弃

    # 7. 反转和复制
    print("\n7. 反转和复制:")

    dq12 = deque([1, 2, 3, 4, 5])
    print(f"原始dq12: {dq12}")

    # 反转
    dq12.reverse()
    print(f"反转后dq12: {dq12}")

    # 浅复制
    dq13 = dq12.copy()
    print(f"复制后dq13: {dq13}")

    # 8. 实际应用场景
    print("\n8. 实际应用场景:")

    # 场景1：队列实现（FIFO）
    print("场景1: 队列实现（FIFO）")

    queue = deque()

    # 入队
    queue.append("任务1")
    queue.append("任务2")
    queue.append("任务3")
    print(f"入队后队列: {queue}")

    # 出队
    while queue:
        task = queue.popleft()
        print(f"处理任务: {task}")

    # 场景2：栈实现（LIFO）
    print("\n场景2: 栈实现（LIFO）")

    stack = deque()

    # 压栈
    stack.append("页面1")
    stack.append("页面2")
    stack.append("页面3")
    print(f"压栈后: {stack}")

    # 弹栈
    while stack:
        page = stack.pop()
        print(f"返回页面: {page}")

    # 场景3：滑动窗口
    print("\n场景3: 滑动窗口")

    def sliding_window_max(nums, k):
        """使用deque实现滑动窗口最大值"""
        if not nums:
            return []

        result = []
        dq = deque()  # 存储索引

        for i in range(len(nums)):
            # 移除超出窗口范围的元素
            if dq and dq[0] < i - k + 1:
                dq.popleft()

            # 移除比当前元素小的元素
            while dq and nums[dq[-1]] < nums[i]:
                dq.pop()

            dq.append(i)

            # 当窗口形成时，添加结果
            if i >= k - 1:
                result.append(nums[dq[0]])

        return result

    nums = [1, 3, -1, -3, 5, 3, 6, 7]
    k = 3
    print(f"数组: {nums}")
    print(f"窗口大小: {k}")
    print(f"滑动窗口最大值: {sliding_window_max(nums, k)}")

    # 场景4：回文检查
    print("\n场景4: 回文检查")

    def is_palindrome(s):
        """使用deque检查回文"""
        # 预处理字符串：转小写，去除非字母数字字符
        chars = deque()
        for ch in s.lower():
            if ch.isalnum():
                chars.append(ch)

        # 从两端比较字符
        while len(chars) > 1:
            if chars.popleft() != chars.pop():
                return False
        return True

    test_strings = ["A man, a plan, a canal: Panama", "race a car", "hello"]
    for s in test_strings:
        print(f"'{s}' 是回文: {is_palindrome(s)}")

    # 场景5：任务调度器
    print("\n场景5: 任务调度器")

    class TaskScheduler:
        def __init__(self):
            self.tasks = deque()
            self.max_tasks = 10

        def add_task(self, task):
            if len(self.tasks) >= self.max_tasks:
                # 移除最旧的任务
                old_task = self.tasks.popleft()
                print(f"任务队列已满，移除任务: {old_task}")
            self.tasks.append(task)
            print(f"添加任务: {task}")

        def process_tasks(self):
            print("处理任务:")
            while self.tasks:
                task = self.tasks.popleft()
                print(f"  执行任务: {task}")

    scheduler = TaskScheduler()
    for i in range(12):
        scheduler.add_task(f"任务{i+1}")
    scheduler.process_tasks()

    # 9. 性能提示
    print("\n9. 性能提示:")
    print("1. deque从两端添加/删除元素是O(1)，比列表的O(n)更高效")
    print("2. deque的随机访问是O(n)，比列表的O(1)慢")
    print("3. 如果需要频繁从两端操作，使用deque而不是list")
    print("4. 如果需要频繁随机访问，使用list而不是deque")
    print("5. deque是线程安全的，可以在多线程环境中使用")
    print("6. 使用maxlen参数可以创建固定长度的deque")
    print("7. rotate()操作可以高效地旋转deque")
    print("8. deque使用双向链表实现，内存开销比列表稍大")

    # 10. 与列表的性能比较
    print("\n10. 与列表的性能比较:")

    import time

    # 测试从左端添加元素的性能
    test_size = 10000

    # 测试列表
    start = time.time()
    lst = []
    for i in range(test_size):
        lst.insert(0, i)  # 列表的insert(0)是O(n)
    list_time = time.time() - start

    # 测试deque
    start = time.time()
    dq = deque()
    for i in range(test_size):
        dq.appendleft(i)  # deque的appendleft是O(1)
    deque_time = time.time() - start

    print(f"从左端添加{test_size}个元素:")
    print(f"  列表: {list_time:.4f}秒")
    print(f"  deque: {deque_time:.4f}秒")
    print(f"  deque比列表快{list_time/deque_time:.1f}倍")

    print("\n========== Python双端队列示例结束 ==========")


if __name__ == "__main__":
    main()

"""
@file priority_queue.py
@brief Python优先队列(priority queue)用法示例

优先队列是一种特殊的队列，元素按照优先级顺序出队
Python中可以使用heapq模块或queue.PriorityQueue实现
特点：
1. 优先级顺序：优先级高的元素先出队
2. 最小堆：默认最小元素优先级最高（最小堆）
3. 高效操作：插入和删除最小元素的时间复杂度为O(log n)
4. 线程安全：queue.PriorityQueue是线程安全的

常用实现方式：
1. heapq模块：基于列表的最小堆实现
2. queue.PriorityQueue：线程安全的优先队列

时间复杂度：
- 插入元素：O(log n)
- 删除最小元素：O(log n)
- 获取最小元素：O(1)
"""

import heapq
import queue
import random


def main():
    print("========== Python优先队列(priority queue)用法示例 ==========")

    # 1. 使用heapq模块实现优先队列
    print("\n1. 使用heapq模块实现优先队列:")

    # 创建空堆（列表）
    heap = []
    print(f"空堆: {heap}")

    # 插入元素
    heapq.heappush(heap, 5)
    heapq.heappush(heap, 2)
    heapq.heappush(heap, 8)
    heapq.heappush(heap, 1)
    heapq.heappush(heap, 3)
    print(f"插入元素后堆: {heap}")
    print(f"堆性质: 最小元素总是在位置0: {heap[0]}")

    # 弹出最小元素
    min_element = heapq.heappop(heap)
    print(f"弹出最小元素: {min_element}, 剩余堆: {heap}")

    min_element = heapq.heappop(heap)
    print(f"再次弹出最小元素: {min_element}, 剩余堆: {heap}")

    # 2. heapq基本操作
    print("\n2. heapq基本操作:")

    # 堆化现有列表
    data = [9, 5, 7, 3, 1, 8, 4, 6, 2]
    heapq.heapify(data)
    print(f"原始列表: [9, 5, 7, 3, 1, 8, 4, 6, 2]")
    print(f"堆化后: {data}")

    # 弹出最小元素并插入新元素
    min_val = heapq.heapreplace(data, 0)
    print(f"heapreplace: 弹出{min_val}, 插入0, 堆: {data}")

    # 获取n个最大/最小元素
    largest = heapq.nlargest(3, data)
    smallest = heapq.nsmallest(3, data)
    print(f"最大的3个元素: {largest}")
    print(f"最小的3个元素: {smallest}")

    # 3. 复杂元素的优先队列
    print("\n3. 复杂元素的优先队列:")

    # 使用元组实现优先级
    tasks = []
    heapq.heappush(tasks, (3, "低优先级任务"))
    heapq.heappush(tasks, (1, "高优先级任务"))
    heapq.heappush(tasks, (2, "中优先级任务"))

    print("按优先级处理任务:")
    while tasks:
        priority, task = heapq.heappop(tasks)
        print(f"  优先级{priority}: {task}")

    # 自定义对象的优先队列
    print("\n自定义对象优先队列:")

    class Task:
        def __init__(self, priority, description):
            self.priority = priority
            self.description = description

        def __lt__(self, other):
            # 定义小于运算符，用于堆比较
            return self.priority < other.priority

        def __repr__(self):
            return f"Task(priority={self.priority}, description='{self.description}')"

    task_heap = []
    heapq.heappush(task_heap, Task(3, "写文档"))
    heapq.heappush(task_heap, Task(1, "修复紧急bug"))
    heapq.heappush(task_heap, Task(2, "代码审查"))

    while task_heap:
        task = heapq.heappop(task_heap)
        print(f"  处理: {task}")

    # 4. 使用queue.PriorityQueue
    print("\n4. 使用queue.PriorityQueue:")

    pq = queue.PriorityQueue()

    # 插入元素
    pq.put((3, "任务C"))
    pq.put((1, "任务A"))
    pq.put((2, "任务B"))

    print("PriorityQueue中的任务:")
    while not pq.empty():
        priority, task = pq.get()
        print(f"  优先级{priority}: {task}")
        pq.task_done()

    # 5. 实际应用场景
    print("\n5. 实际应用场景:")

    # 场景1：任务调度系统
    print("场景1: 任务调度系统")

    class TaskScheduler:
        def __init__(self):
            self.heap = []
            self.counter = 0  # 用于处理优先级相同的情况

        def add_task(self, priority, task):
            """添加任务"""
            # 使用counter确保相同优先级时按添加顺序处理
            heapq.heappush(self.heap, (priority, self.counter, task))
            self.counter += 1
            print(f"添加任务: 优先级{priority}, {task}")

        def process_tasks(self):
            """处理所有任务"""
            print("处理任务:")
            while self.heap:
                priority, _, task = heapq.heappop(self.heap)
                print(f"  执行[优先级{priority}]: {task}")

    scheduler = TaskScheduler()
    scheduler.add_task(2, "发送日报")
    scheduler.add_task(1, "处理用户投诉")  # 最高优先级
    scheduler.add_task(2, "更新文档")
    scheduler.add_task(3, "整理代码")
    scheduler.add_task(1, "修复安全漏洞")  # 最高优先级

    scheduler.process_tasks()

    # 场景2：合并有序序列
    print("\n场景2: 合并K个有序列表")

    def merge_k_sorted_lists(lists):
        """合并K个有序列表"""
        heap = []
        result = []

        # 将每个列表的第一个元素加入堆
        for i, lst in enumerate(lists):
            if lst:  # 列表非空
                heapq.heappush(heap, (lst[0], i, 0))

        while heap:
            val, list_idx, element_idx = heapq.heappop(heap)
            result.append(val)

            # 如果当前列表还有下一个元素，加入堆
            if element_idx + 1 < len(lists[list_idx]):
                next_val = lists[list_idx][element_idx + 1]
                heapq.heappush(heap, (next_val, list_idx, element_idx + 1))

        return result

    lists = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]

    print(f"要合并的列表: {lists}")
    merged = merge_k_sorted_lists(lists)
    print(f"合并后: {merged}")

    # 场景3：数据流的中位数
    print("\n场景3: 数据流的中位数")

    class MedianFinder:
        def __init__(self):
            # 最大堆（存储较小的一半，Python中最大堆用负数实现）
            self.max_heap = []
            # 最小堆（存储较大的一半）
            self.min_heap = []

        def add_num(self, num):
            """添加数字"""
            if not self.max_heap or num <= -self.max_heap[0]:
                heapq.heappush(self.max_heap, -num)
            else:
                heapq.heappush(self.min_heap, num)

            # 平衡两个堆
            if len(self.max_heap) > len(self.min_heap) + 1:
                heapq.heappush(self.min_heap, -heapq.heappop(self.max_heap))
            elif len(self.min_heap) > len(self.max_heap):
                heapq.heappush(self.max_heap, -heapq.heappop(self.min_heap))

        def find_median(self):
            """查找中位数"""
            if len(self.max_heap) == len(self.min_heap):
                return (-self.max_heap[0] + self.min_heap[0]) / 2
            else:
                return -self.max_heap[0]

        def __str__(self):
            return (
                f"最大堆(小的一半): {-self.max_heap[0] if self.max_heap else '空'}, "
                f"最小堆(大的一半): {self.min_heap[0] if self.min_heap else '空'}"
            )

    finder = MedianFinder()
    data_stream = [5, 2, 8, 3, 1, 9, 4]

    print(f"数据流: {data_stream}")
    for num in data_stream:
        finder.add_num(num)
        print(f"添加 {num}: 当前中位数 = {finder.find_median():.1f}")

    # 场景4：Dijkstra算法（简化版）
    print("\n场景4: Dijkstra算法（简化版）")

    def dijkstra(graph, start):
        """Dijkstra最短路径算法"""
        distances = {node: float("inf") for node in graph}
        distances[start] = 0
        heap = [(0, start)]  # (距离, 节点)

        while heap:
            current_dist, current_node = heapq.heappop(heap)

            # 如果找到更短距离，跳过
            if current_dist > distances[current_node]:
                continue

            for neighbor, weight in graph[current_node].items():
                distance = current_dist + weight

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    heapq.heappush(heap, (distance, neighbor))

        return distances

    # 示例图
    graph = {
        "A": {"B": 1, "C": 4},
        "B": {"A": 1, "C": 2, "D": 5},
        "C": {"A": 4, "B": 2, "D": 1},
        "D": {"B": 5, "C": 1},
    }

    print(f"图: {graph}")
    distances = dijkstra(graph, "A")
    print(f"从A出发的最短距离: {distances}")

    # 场景5：Top K问题
    print("\n场景5: Top K问题")

    def top_k_frequent(nums, k):
        """返回出现频率最高的k个元素"""
        from collections import Counter

        # 统计频率
        freq = Counter(nums)
        print(f"元素频率: {freq}")

        # 使用最小堆找到Top K
        heap = []
        for num, count in freq.items():
            heapq.heappush(heap, (count, num))
            if len(heap) > k:
                heapq.heappop(heap)  # 移除频率最小的

        # 提取结果
        result = []
        while heap:
            count, num = heapq.heappop(heap)
            result.append(num)

        return result[::-1]  # 反转得到频率从高到低

    nums = [1, 1, 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 5]
    k = 3
    print(f"数组: {nums}")
    print(f"出现频率最高的{k}个元素: {top_k_frequent(nums, k)}")

    # 6. 性能提示
    print("\n6. 性能提示:")
    print("1. heapq基于列表实现，插入和删除是O(log n)")
    print("2. heapify()是O(n)操作，比逐个插入更高效")
    print("3. PriorityQueue是线程安全的，但比heapq慢")
    print("4. 对于大量数据，考虑使用斐波那契堆等更高效的数据结构")
    print("5. 使用元组(priority, data)时，优先级相同的元素按data排序")
    print("6. 可以使用(priority, counter, data)确保相同优先级按添加顺序处理")
    print("7. nlargest()和nsmallest()对于小n是高效的")

    # 7. 常见问题
    print("\n7. 常见问题:")

    # 问题1：最大堆的实现
    print("问题1: 最大堆的实现")
    print("Python的heapq是最小堆，要实现最大堆可以使用负数:")

    max_heap = []
    for num in [1, 3, 5, 7, 9]:
        heapq.heappush(max_heap, -num)

    print(f"最大堆(使用负数): {max_heap}")
    while max_heap:
        print(f"  弹出最大元素: {-heapq.heappop(max_heap)}")

    # 问题2：堆中元素的更新
    print("\n问题2: 堆中元素的更新")
    print("heapq不支持直接更新元素，需要重新构建堆或使用其他数据结构")

    # 问题3：自定义比较函数
    print("\n问题3: 自定义比较函数")
    print("对于自定义对象，需要实现__lt__方法或使用元组包装")

    class Person:
        def __init__(self, name, age):
            self.name = name
            self.age = age

        def __lt__(self, other):
            return self.age < other.age  # 按年龄比较

        def __repr__(self):
            return f"{self.name}({self.age})"

    people_heap = []
    heapq.heappush(people_heap, Person("Alice", 30))
    heapq.heappush(people_heap, Person("Bob", 25))
    heapq.heappush(people_heap, Person("Charlie", 35))

    print("按年龄排序的人员:")
    while people_heap:
        person = heapq.heappop(people_heap)
        print(f"  {person}")

    print("\n========== Python优先队列示例结束 ==========")


if __name__ == "__main__":
    main()

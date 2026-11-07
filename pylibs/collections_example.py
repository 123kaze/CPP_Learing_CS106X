"""
@file collections_example.py
@brief Python collections 用法示例：队列、计数器和分组

特点与复杂度：
1. deque 双端入队 / 出队 O(1)，适合 BFS 和单调队列。
2. Counter 统计 n 个元素平均 O(n)，适合频次统计。
3. defaultdict 自动提供缺失键的默认值，适合邻接表和分组。
4. BFS 为 O(V+E)，单调队列滑动窗口为 O(n)。
"""

from collections import Counter, defaultdict, deque


def bfs_distances(graph, start):
    """无权图最短距离；graph 为邻接表，不可达点的距离为 -1。"""
    distances = [-1] * len(graph)
    distances[start] = 0
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if distances[neighbor] == -1:
                # 入队时标记，避免同一节点被重复加入队列。
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)
    return distances


def sliding_window_max(nums, k):
    """返回每个长度为 k 的窗口最大值；没有完整窗口时返回空列表。"""
    if k <= 0:
        raise ValueError("窗口大小必须为正整数")
    queue = deque()
    answer = []
    for i, value in enumerate(nums):
        while queue and queue[0] <= i - k:
            queue.popleft()
        # 存下标而不是值，队列内的值单调递减。
        while queue and nums[queue[-1]] <= value:
            queue.pop()
        queue.append(i)
        if i >= k - 1:
            answer.append(nums[queue[0]])
    return answer


def main():
    print("========== Python collections 用法示例 ==========")

    # 1. 双端队列
    print("\n1. deque 基本操作:")
    queue = deque([2, 3])
    queue.appendleft(1)
    queue.append(4)
    print(f"两端添加: {list(queue)}")
    print(f"popleft(): {queue.popleft()}, pop(): {queue.pop()}")
    queue.rotate(1)
    print(f"向右旋转一步: {list(queue)}")
    recent = deque([1, 2, 3], maxlen=3)
    recent.append(4)
    print(f"maxlen=3 自动丢弃另一端: {list(recent)}")

    # 2. 频次统计
    print("\n2. Counter 计数:")
    counts = Counter("banana")
    print(f"字符频次: {dict(counts)}")
    print(f"a 出现 {counts['a']} 次，缺失的 x 出现 {counts['x']} 次")
    print(f"最常见的两个字符: {counts.most_common(2)}")
    print(f"变位词判断: {Counter('listen') == Counter('silent')}")
    counts.subtract("aaaa")
    print(f"subtract 保留负计数: {dict(counts)}")
    print(f"+counts 只保留正计数: {dict(+counts)}")

    # 3. 自动初始化分组
    print("\n3. defaultdict 分组:")
    groups = defaultdict(list)
    for word in ("eat", "tea", "tan", "ate", "nat", "bat"):
        groups["".join(sorted(word))].append(word)
    print(f"按变位词分组: {list(groups.values())}")
    print(f"get 不会创建缺失键: {groups.get('missing')}")
    print(f"缺失键是否已创建: {'missing' in groups}")

    # 4. 算法应用
    print("\n4. 算法题应用:")
    graph = [[1, 2], [0, 3], [0, 3], [1, 2], []]
    print(f"BFS 从节点 0 出发的距离: {bfs_distances(graph, 0)}")
    nums = [1, 3, -1, -3, 5, 3, 6, 7]
    print(f"数组: {nums}, 窗口大小: 3")
    print(f"滑动窗口最大值: {sliding_window_max(nums, 3)}")

    # 5. 性能和易错点
    print("\n5. 性能和易错点:")
    print("1. BFS 用 deque.popleft()，不要用 O(n) 的 list.pop(0)")
    print("2. deque 中间索引访问是 O(n)，不适合大量随机访问")
    print("3. deque(maxlen=k) 满时会丢元素，不要用于不能丢节点的 BFS")
    print("4. defaultdict[key] 会创建缺失键，get(key) 不会")
    print("5. Counter 的 len 是键的个数，不是频次之和")
    print("\n========== collections 示例结束 ==========")


if __name__ == "__main__":
    main()

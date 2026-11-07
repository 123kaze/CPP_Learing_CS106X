"""
@file heapq_example.py
@brief Python heapq 用法示例：优先队列和堆算法

特点与复杂度：
1. 默认是最小堆，heap[0] 是最小值，但整个列表并不有序。
2. heapify 原地建堆 O(n)，heappush / heappop 为 O(log n)。
3. 用负数模拟最大堆，兼容较旧的 OJ Python 版本。
4. 合并最小代价 O(n log n)，适用于非负权重。
5. 本示例 Dijkstra 使用懒删除，时间 O((V+E) log(V+E))，空间 O(V+E)。
"""

import heapq
from math import inf


def minimum_merge_cost(weights):
    """每次合并两个非负权重，代价为权重之和，返回最小总代价。"""
    heap = list(weights)
    if any(weight < 0 for weight in heap):
        raise ValueError("权重必须非负")
    heapq.heapify(heap)
    total = 0
    while len(heap) > 1:
        merged = heapq.heappop(heap) + heapq.heappop(heap)
        total += merged
        heapq.heappush(heap, merged)
    return total


def dijkstra(graph, start):
    """非负权图最短路；邻接表元素为 (邻点, 权重)，不可达为 inf。"""
    distances = [inf] * len(graph)
    distances[start] = 0
    heap = [(0, start)]
    while heap:
        distance, node = heapq.heappop(heap)
        # 不做 decrease-key，允许重复入堆，弹出时跳过过期状态。
        if distance != distances[node]:
            continue
        for neighbor, weight in graph[node]:
            candidate = distance + weight
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heapq.heappush(heap, (candidate, neighbor))
    return distances


def main():
    print("========== Python heapq 用法示例 ==========")

    # 1. 建堆、入堆和出堆
    print("\n1. 最小堆基本操作:")
    heap = [5, 1, 7, 3]
    heapq.heapify(heap)
    print(f"建堆后最小值: {heap[0]}")
    heapq.heappush(heap, 2)
    print(f"入堆 2，弹出最小值: {heapq.heappop(heap)}")
    ordered = []
    while heap:
        ordered.append(heapq.heappop(heap))
    print(f"依次弹出才是有序的: {ordered}")

    # 2. 最大堆和 Top K
    print("\n2. 最大堆和 Top K:")
    nums = [5, 1, 7, 3, 9, 2]
    max_heap = [-x for x in nums]
    heapq.heapify(max_heap)
    print(f"负数模拟最大堆，最大值: {-heapq.heappop(max_heap)}")
    print(f"最大的 3 个数: {heapq.nlargest(3, nums)}")
    print(f"最小的 3 个数: {heapq.nsmallest(3, nums)}")

    # 3. 元组优先级
    print("\n3. 元组优先级:")
    tasks = []
    for sequence, (priority, name) in enumerate([(2, "任务A"), (1, "任务B"), (1, "任务C")]):
        heapq.heappush(tasks, (priority, sequence, name))
    print("按优先级排序，相同优先级按入队次序排序:")
    while tasks:
        print(heapq.heappop(tasks))

    # 4. 组合操作
    print("\n4. heappushpop 与 heapreplace:")
    heap = [2, 4, 6]
    print(f"heappushpop(heap, 1): {heapq.heappushpop(heap, 1)}, 堆: {heap}")
    print(f"heapreplace(heap, 1): {heapq.heapreplace(heap, 1)}, 堆: {heap}")
    print("前者先加入再弹出最小值；后者先弹出旧堆顶再加入，要求堆非空")

    # 5. 算法应用
    print("\n5. 算法题应用:")
    print(f"合并 [1, 2, 3, 4] 的最小代价: {minimum_merge_cost([1, 2, 3, 4])}")
    graph = [[(1, 4), (2, 1)], [(3, 1)], [(1, 2), (3, 5)], [], []]
    print(f"Dijkstra 从节点 0 出发的距离: {dijkstra(graph, 0)}")

    # 6. 易错点
    print("\n6. 易错点:")
    print("1. 空堆不能 heappop 或访问 heap[0]")
    print("2. 元组按字典序比较；优先级相同时可能继续比较任务对象，用序号打破平局")
    print("3. Dijkstra 要求边权非负，带负权时应选择其他算法")
    print("4. heapify 会修改原列表，需要保留输入时先复制")
    print("\n========== heapq 示例结束 ==========")


if __name__ == "__main__":
    main()

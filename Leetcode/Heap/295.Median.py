import heapq

class MedianFinder:
    def __init__(self):
        # 最大堆（存储较小的一半），用负数模拟
        self.left = []  # 最大堆
        # 最小堆（存储较大的一半）
        self.right = []  # 最小堆

    def addNum(self, num: int) -> None:
        # 决定放入哪个堆
        if not self.left or num <= -self.left[0]:
            heapq.heappush(self.left, -num)
        else:
            heapq.heappush(self.right, num)

        # 平衡两个堆的大小，使 left 最多比 right 多一个元素
        if len(self.left) > len(self.right) + 1:
            heapq.heappush(self.right, -heapq.heappop(self.left))
        elif len(self.right) > len(self.left):
            heapq.heappush(self.left, -heapq.heappop(self.right))

    def findMedian(self) -> float:
        if len(self.left) == len(self.right):
            # 偶数个元素，取两个堆顶的平均值
            return (-self.left[0] + self.right[0]) / 2.0
        else:
            # 奇数个元素，取 left 堆顶（因为 left 多一个）
            return -self.left[0]
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

from typing import Optional, List
import heapq

class Solution:
    def mergeKLists(self, lists: List[Optional[ListNode]]) -> Optional[ListNode]:
        dummy = ListNode(0)
        tail = dummy
        heap = []

        # 使用索引来避免比较 ListNode
        for i, node in enumerate(lists):
            if node:
                heapq.heappush(heap, (node.val, i, node))

        while heap:
            val, i, node = heapq.heappop(heap)
            tail.next = node
            tail = tail.next
            if node.next:
                # 注意：这里需要传递相同的 i 值，或者用一个新的计数
                # 如果 i 固定，当两个节点值相等时，会继续用 i 来比较
                heapq.heappush(heap, (node.next.val, i, node.next))

        return dummy.next
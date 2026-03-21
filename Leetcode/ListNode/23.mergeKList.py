# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
from typing import Optional,List
import heapq
class Solution:
    def mergeKLists(self, lists: List[Optional[ListNode]]) -> Optional[ListNode]:
        def mergeTwoLists(l1: ListNode, l2: ListNode) -> Optional[ListNode]:
            if not l1 or not l2:
                return l1 or l2
            cur = ListNode(0)
            tail = cur

            while l1 and l2:
                if l1.val <= l2.val:
                    tail.next = l1
                    l1 = l1.next
                else:
                    tail.next = l2
                    l2 = l2.next
                tail = tail.next
            tail.next = l1 or l2
            return cur.next

        def merge(l:int,r:int):
            if l == r:
                return lists[l]
            if l > r:
                return None

            mid = (l + r) // 2
            l1 = merge(l,mid)
            r1 = merge(mid+1,r)
            return mergeTwoLists(l1,r1)

        if not lists:
            return None
        return merge(0,len(lists)-1)





    def mergeKLists(self, lists: List[Optional[ListNode]]) -> Optional[ListNode]:
        heap = []
        n = len(lists)
        for i in range(n):
            heapq.heappush(heap, lists[i].val)


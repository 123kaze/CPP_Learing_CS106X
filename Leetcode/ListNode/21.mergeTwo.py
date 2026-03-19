# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
from  typing import Optional
import heapq
class Solution:
    def mergeTwoLists(self, list1: Optional[ListNode], list2: Optional[ListNode]) -> Optional[ListNode]:
        if not list1:
            return list2
        if not list2:
            return list1
        idx1 = 1
        current = [(list1.val,idx1, list1),(list2.val,idx1+1, list2)]
        idx1+=1
        dummy = ListNode(0)
        head = dummy
        heapq.heapify(current)
        while current:
            val,idx,node = heapq.heappop(current)
            idx1+=1
            dummy.next = node
            dummy = dummy.next
            node = node.next
            if node:
                heapq.heappush(current, (node.val,idx1+1,node))


        return head.next



class Solution:
    def mergeTwoLists(self, list1: Optional[ListNode], list2: Optional[ListNode]) -> Optional[ListNode]:
        if list1 is None: return list2  # 注：如果都为空则返回空
        if list2 is None: return list1
        if list1.val < list2.val:
            list1.next = self.mergeTwoLists(list1.next, list2)
            return list1
        list2.next = self.mergeTwoLists(list1, list2.next)
        return list2





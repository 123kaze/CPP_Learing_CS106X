# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

from typing import  Optional,List
class Solution:
    def mergeTwoLists(self, l1: ListNode, l2: ListNode) -> ListNode:
            if not l1:
                return l2
            if not l2:
                return l1
            if l1.val < l2.val:
                l1.next = self.mergeTwoLists(l1.next, l2)
                return l1
            else:
                l2.next = self.mergeTwoLists(l1, l2.next)
                return l2

    def mergeKLists(self, lists: List[Optional[ListNode]]) -> Optional[ListNode]:
        if not lists:
            return None
        n = len(lists)
        def merge(l:int,r:int):
            if l == r:
                return lists[l]
            if l > r:
                return None
            mid = (l + r) // 2
            l1 = merge(l, mid)
            r2 = merge(mid+1, r)
            return self.mergeTwoLists(l1, r2)

        return merge(0,n-1)





# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
from typing import Optional
class Solution:
    def middleNode(self, head: Optional[ListNode]) -> Optional[ListNode]:
        slow = fast = head
        while fast and fast.next:
            pre = slow
            slow = slow.next
            fast = fast.next.next
        
        pre.next = None
        return slow
    
    def mergeTwoList(self,head,other)->Optional[ListNode]:
        dummy= cur = ListNode(0)
        while head and other:
            if head.val >= other.val:
                cur.next = other
                cur = cur.next
                other = other.next
            else:
                cur.next = head
                cur = cur.next
                head = head.next
        cur.next = head if head else other
        return dummy.next
    
    def sortList(self,head:Optional[ListNode])->Optional[ListNode]:
        if not head or not head.next:
            return head
        mid = self.middleNode(head)
        head1= self.sortList(mid)
        head2 = self.sortList(head)
        headn = self.mergeTwoList(head1,head2)
        return headn
        
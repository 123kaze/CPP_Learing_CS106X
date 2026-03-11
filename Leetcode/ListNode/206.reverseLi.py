# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
from typing import Optional

class Solution:
    def reverseList(self, head: Optional[ListNode]) -> Optional[ListNode]:
        
        def dfs(head: Optional[ListNode]):
            if not head or not head.next:
                return head
            newhead = dfs(head.next)
            head.next.next = head
            head.next = None
            return newhead
        
        return dfs(head)

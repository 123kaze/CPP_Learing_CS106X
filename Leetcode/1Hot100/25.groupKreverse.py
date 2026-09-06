class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

from typing import Optional        
class Solution:
    def reverseKGroup(self, head: Optional[ListNode], k: int) -> Optional[ListNode]:
        n = 0
        cur = head

        while cur:
            n += 1
            cur = cur.next

        last_tail = dummy = ListNode(next=head)

        while n>=k:
            n-=k
            pre = None
            cur = last_tail.next
            for _ in range(k):
                nxt = cur.next
                cur.next = pre
                pre = cur
                cur = nxt

            t = last_tail.next
            last_tail.next = pre
            t.next = cur
            last_tail = t

        return dummy.next
            



           
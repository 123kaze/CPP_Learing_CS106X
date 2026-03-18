# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

from typing import Optional
class Solution:
    def removeNthFromEnd(self, head: Optional[ListNode], n: int) -> Optional[ListNode]:
        '''
        非常简单的递归做法
        :param head:
        :param n:
        :return:
        '''
        p = head
        nth = 0
        def dfs(node):
            nonlocal nth
            if node is None:
                return None
            newnode = dfs(node.next)
            nth += 1
            if nth == n:
                return newnode
            node.next = newnode
            return node
        return dfs(head)




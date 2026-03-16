# Definition for singly-linked list.
class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None
from typing import Optional
class Solution:
    def hasCycle(self, head: Optional[ListNode]) -> bool:
        visited = []

        def dfs(node):
            nonlocal visited
            if not node:
                return False
            if node and node in visited:
                return True
            visited.append(node)
            return dfs(node.next)

        return dfs(head)
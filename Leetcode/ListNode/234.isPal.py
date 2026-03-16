# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

from typing import  Optional
class Solution:
    def isPalindrome(self, head: Optional[ListNode]) -> bool:
        visited = []
        idx = 0
        while head:
            visited.append(head.val)
            head = head.next

        return  visited == list(reversed(visited))
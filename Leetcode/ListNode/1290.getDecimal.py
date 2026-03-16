# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
from typing import  Optional
class Solution:
    def getDecimalValue(self, head: ListNode) -> int:
# 先把链表值转成字符串
        bits = ""
        while head:
            bits += str(head.val)
            head = head.next

# 方法1：int() 指定进制
        return  int(bits, 2)

# 方法2：使用 int.from_bytes() 或 bin()/int() 组合
# 但对于二进制字符串，int(bits, 2) 最简单
# 但对于二进制字符串，int(bits, 2) 最简单

# Definition for a Node.
class Node:
    def __init__(self, x: int, next: 'Node' = None, random: 'Node' = None):
        self.val = int(x)
        self.next = next
        self.random = random
from typing import Optional
from collections import defaultdict
"""
# Definition for a Node.
class Node:
    def __init__(self, x: int, next: 'Node' = None, random: 'Node' = None):
        self.val = int(x)
        self.next = next
        self.random = random
"""

class Solution:
    def copyRandomList(self, head: 'Optional[Node]') -> 'Optional[Node]':
        if not head:
            return None

        # 创建哈希表，存储原节点到新节点的映射
        hash_map = {}

        # 第一遍遍历：创建所有新节点，并建立映射
        curr = head
        while curr:
            hash_map[curr] = Node(curr.val)
            curr = curr.next

        # 第二遍遍历：设置新节点的next和random指针
        curr = head
        while curr:
            if curr.next:
                hash_map[curr].next = hash_map[curr.next]
            if curr.random:
                hash_map[curr].random = hash_map[curr.random]
            curr = curr.next

        return hash_map[head]


'''
优雅版本
'''

class Solution:
    def copyRandomList(self, head: 'Optional[Node]') -> 'Optional[Node]':
        # 复制每个节点，把新节点直接插到原节点的后面
        cur = head
        while cur:
            cur.next = Node(cur.val, cur.next)
            cur = cur.next.next

        '1 1 2 2 33 4 4'
        # 遍历交错链表中的原链表节点
        cur = head
        while cur:
            if cur.random:
                # 要复制的 random 是 cur.random 的下一个节点
                cur.next.random = cur.random.next
            cur = cur.next.next

        # 把交错链表分离成两个链表
        tail = dummy = Node(0, head)
        cur = head
        while cur:
            copy = cur.next  # 新节点
            tail.next = copy  # 把新节点插在 tail 的后面，构建新的链表
            cur.next = copy.next  # 恢复原节点的 next
            cur = cur.next
            tail = tail.next

        return dummy.next


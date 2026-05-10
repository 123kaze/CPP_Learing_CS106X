from typing import Optional


class Node:
    __slots__ = 'val', 'prev', 'next','key'
    def __init__(self, key=0, val=0) -> None:
        self.key = key
        self.val = val

class LRUCache:

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}
        self.dummy = Node()
        self.dummy.prev = self.dummy
        self.dummy.next = self.dummy
        self.key_to_node = {}

    # 得到 key 的节点
    def getnode(self,key: int) -> Optional[Node]:
        if key not in self.key_to_node:
            return None
        node = self.key_to_node[key]
        self.remove(node)
        self.push_frount(node)
        return node

    def remove(self,node: Optional[Node]) -> None:
        if node is None:
            return
        node.next.prev = node.prev
        node.prev.next = node.next
    def push_frount(self,node: Optional[Node]) -> None:
        if node is None:
            return
        node.next = self.dummy.next
        node.prev = self.dummy
        self.dummy.next.prev = node
        self.dummy.next = node

    def get(self, key: int) -> int:
        node = self.getnode(key)
        return node.val if node else -1


    def put(self, key: int, value: int) -> None:
        node = self.getnode(key)
        if node:
            node.val = value
            return
        self.key_to_node[key] = node = Node(key, value)
        self.push_frount(node)
        if len(self.key_to_node) > self.capacity:
            backnode = self.dummy.prev
            del self.key_to_node[backnode.key]
            self.remove(backnode)


# Your LRUCache object will be instantiated and called as such:
# obj = LRUCache(capacity)
# param_1 = obj.get(key)
# obj.put(key,value)
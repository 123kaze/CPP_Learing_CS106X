class Node:
    def __init__(self, val=0, key=0) -> None:
        self.val = val
        self.key = key
        self.next = None
        self.pre = None


class LRUCache:

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.map = {}
        self.dummy = Node()
        self.dummy.pre = self.dummy
        self.dummy.next = self.dummy

    def getNode(self, key: int):
        if key not in self.map:
            return None
        node = self.map[key]
        self.remove(node)
        self.pf(node)
        return node

    def remove(self, node):
        node.pre.next = node.next
        node.next.pre = node.pre

    def pf(self, node):
        h = self.dummy.next
        h.pre = node
        self.dummy.next = node
        node.pre = self.dummy
        node.next = h

    def get(self, key: int) -> int:
        node = self.getNode(key)
        return node.val if node and node.val != 0 else -1

    def put(self, key: int, value: int) -> None:
        node = self.getNode(key)
        if node:
            node.val = value
            return

        self.map[key] = node = Node(value, key)
        self.pf(node)

        if len(self.map) > self.capacity:
            node1 = self.dummy.pre
            del self.map[node1.key]
            self.remove(node1)


# Your LRUCache object will be instantiated and called as such:
# obj = LRUCache(capacity)
# param_1 = obj.get(key)
# obj.put(key,value)

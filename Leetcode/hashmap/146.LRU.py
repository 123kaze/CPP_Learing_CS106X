class Node:
    def __init__(self, key=0, value=0):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> Node
        # 使用伪头部和伪尾部，简化边界条件处理
        self.head = Node()
        self.tail = Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        node = self.cache[key]
        self._move_to_head(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            new_node = Node(key, value)
            self.cache[key] = new_node
            self._add_to_head(new_node)
            if len(self.cache) > self.capacity:
                removed = self._remove_tail()
                del self.cache[removed.key]

    # --- 内部辅助方法，确保 O(1) 操作 ---

    def _add_to_head(self, node):
        """将节点插入到伪头部之后"""
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def _remove_node(self, node):
        """删除指定节点"""
        node.prev.next = node.next
        node.next.prev = node.prev

    def _move_to_head(self, node):
        """将现有节点移动到头部（即先删后插）"""
        self._remove_node(node)
        self._add_to_head(node)

    def _remove_tail(self):
        """删除并返回最久未使用的节点"""
        node = self.tail.prev
        self._remove_node(node)
        return node
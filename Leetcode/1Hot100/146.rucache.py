class Node:
    def __init__(self, val=0, key=0) -> None:
        self.val = val
        self.key = key
        self.next = None
        self.prev = None

class LRUCache:

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.dummy = Node()
        self.dummy.next = self.dummy
        self.dummy.prev = self.dummy
        self.key_to = {}     

    def getNode(self,key):
        if key not in self.key_to:
            return None
        node = self.key_to[key]
        self.remove(node)
        self.push(node)
        return node        

    def remove(self,node):
        node.prev.next = node.next
        node.next.prev = node.prev
        node.prev = None
        node.next = None

    def push(self,node):
        
        node.next = self.dummy.next
        node.prev = self.dummy
        node.next.prev = node
        self.dummy.next = node

    def get(self, key: int) -> int:
        return self.getNode(key).val if self.getNode(key) else -1
        

    def put(self, key: int, value: int) -> None:
        if key in self.key_to:
            node = Node(value,key)
            no1 = self.key_to[key]
            self.remove(no1)
            self.push(node)
            self.key_to[key] = node
            return
        else:
            node = Node(value,key)
            self.key_to[key] = node
            self.push(node)
            if len(self.key_to) > self.capacity:
                back = self.dummy.prev
                del self.key_to[back.key]
                self.remove(back)

# Your LRUCache object will be instantiated and called as such:
# obj = LRUCache(capacity)
# param_1 = obj.get(key)
# obj.put(key,value)


n = [1, 10, 12,11, 13, 2, 3, 4, 5, 6, 7, 8, 9,101]
s = list(map(str,n))
s.sort()
print(s)
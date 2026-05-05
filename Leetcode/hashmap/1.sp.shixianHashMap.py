from typing import List
from collections import defaultdict

class HashMap:
    def __init__(self,capacity=100):
        self.capacity = capacity
        self.size = 0
        self.load_factor = 0.75
        self.data = [[] for _ in range(self.capacity)]

    def _hash(self,key):
        return key % self.capacity

    def hash1(self, key):
        # 使用 Python 内置 hash()，支持字符串、浮点数等，并取绝对值
        return abs(hash(key)) % self.capacity

    def put(self,key,value):
        if self.size / self.capacity >= self.load_factor:
            self._resize()

        index = self._hash(key)
        bucket = self.data[index]
        
        for p in bucket:
            if p[0] == key:
                p[1] = value
                return
        bucket.append([key,value])
        self.size += 1

    def get(self,key):
        index = self._hash(key)
        bucket = self.data[index]
        
        for p in bucket:
            if p[0] == key:
                return p[1]
        return None

    def remove(self,key):
        index = self._hash(key)
        bucket = self.data[index]
        
        for i in range(len(bucket)):
            if bucket[i][0] == key:
                bucket.pop(i)
                self.size -= 1
                return
        return None

    def _resize(self):
        old_data = self.data
        self.capacity *= 2
        self.size = 0
        self.data = [[] for _ in range(self.capacity)]
        
        for bucket in old_data:
            for key, value in bucket:
                self.put(key, value)

obj = HashMap()
obj.put(1, 10)
obj.put(1001, 20)
print(obj.get(1))
print(obj.get(1001))
obj.remove(1)
print(obj.get(1))


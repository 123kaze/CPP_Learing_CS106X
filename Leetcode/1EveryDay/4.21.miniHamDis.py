from typing import List
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
    def find(self, i):
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]
    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j

class Solution:
    def minimumHammingDistance(self, source: List[int], target: List[int], allowedSwaps: List[List[int]]) -> int:
        n = len(source)
        uf = UnionFind(n)

        for a,b in allowedSwaps:
            uf.union(a, b)

        from collections import defaultdict,Counter
        groups = defaultdict(Counter)
        for i in range(n):
            root = uf.find(i)
            groups[root][source[i]] += 1

        matches = 0
        for i in range(n):
            root = uf.find(i)
            val = target[i]
            if groups[root][val] > 0:
                matches += 1
                groups[root][val] -= 1


        return n-matches